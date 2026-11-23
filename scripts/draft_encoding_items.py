"""Draft encoding-equivalence items for benchmark v1, for a native speaker to verify.

    uv run python scripts/draft_encoding_items.py --wikipedia data/raw/wikipedia-km \
        --golden tests/golden/normalization.jsonl \
        --out bench/drafts/encoding-equivalence/drafts.jsonl

Builds on scripts/draft_encoding_pairs.py, but works on short Khmer strings (runs of two
to four syllable clusters between spaces, punctuation and digits) from verified golden
fixtures and the Khmer Wikipedia sample instead of single syllables. Three kinds:

- same-attested (A): a string found in the text in a non-canonical encoding, paired
  with its `pheasa.normalize` form.
- same-constructed (A): a canonical string with one cluster typed in another order, or
  with coeng ta typed as coeng da; kept only if `normalize` maps it back exactly.
- different-one-edit (B): two canonical strings, both found in the text, that differ by
  one character (substituted, added or removed). Strings with ZWJ or ZWNJ are skipped,
  so no "different" pair differs only invisibly.

No Khmer is written by this script: every string is taken from the sources or is a
reordering of one. Output is deterministic for a given --seed, and may only be written
under bench/drafts/. Drafts are never scored; only a person promotes them.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

from draft_encoding_pairs import one_substitution

from pheasa import normalize
from pheasa.normalize import COENG, ZWJ, ZWNJ, _clusters

TASK = "encoding-equivalence"
# Characters that make up Khmer words; everything else (spaces, ZWSP, Khmer punctuation
# U+17D4-17D6 and U+17D8-17DA, riel U+17DB, digits U+17E0-17E9, Latin) ends a run.
# Source: Unicode 18.0 UnicodeData.txt, general categories of U+1780-17FF: U+1780-17D3
# are letters and marks (Lo, Mn, Mc), U+17D7 LEK TOO is Lm, U+17DC is Lo, U+17DD is Mn.
RUN = re.compile("[ក-៓ៗៜ៝‌‍]+")
COENG_TA, COENG_DA = COENG + "ត", COENG + "ដ"  # rule 3.8 folds DA into TA
MIN_CLUSTERS, MAX_CLUSTERS = 2, 4


def codepoints(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text)


def runs(text: str) -> list[str]:
    found = []
    for match in RUN.finditer(text):
        run = match.group()
        if MIN_CLUSTERS <= sum(1 for _ in _clusters(run)) <= MAX_CLUSTERS:
            found.append(run)
    return found


def read_sources(wikipedia: Path | None, golden: Path | None) -> list[tuple[str, dict]]:
    """(text, provenance) for every golden fixture input and Wikipedia article."""
    texts = []
    if golden:
        for line in golden.read_text(encoding="utf-8").splitlines():
            if line.strip():
                fixture = json.loads(line)
                provenance = {k: fixture[k] for k in ("source", "license", "retrieved")}
                texts.append((fixture["input"], {**provenance, "from": "golden fixture"}))
    if wikipedia:
        manifest = wikipedia.parent.parent / wikipedia.name / "manifest.jsonl"  # data/raw/X
        pages = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                pages[str(record["pageid"])] = record
        for path in sorted(wikipedia.glob("*.txt")):
            record = pages.get(path.stem)
            if record:
                provenance = {k: record[k] for k in ("source", "license", "retrieved")}
                texts.append(
                    (path.read_text(encoding="utf-8"), {**provenance, "from": "wikipedia"})
                )
    return texts


def units(cluster: str) -> list[str]:
    """A cluster's marks after the base, with each coeng kept with its consonant."""
    out, i = [], 1
    while i < len(cluster):
        step = 2 if cluster[i] == COENG and i + 1 < len(cluster) else 1
        out.append(cluster[i : i + step])
        i += step
    return out


def constructed_variants(canonical: str) -> list[tuple[str, str]]:
    """(variant, kind) pairs that `normalize` maps back to `canonical`."""
    found = []
    if COENG_TA in canonical:
        found.append((canonical.replace(COENG_TA, COENG_DA, 1), "coeng-da"))
    for start, end in _clusters(canonical):
        cluster = canonical[start:end]
        marks = units(cluster)
        if len(marks) < 2 or len(marks) > 5:
            continue
        for order in sorted(set(permutations(marks))):
            typed = cluster[0] + "".join(order)
            if typed != cluster:
                found.append((canonical[:start] + typed + canonical[end:], "reordered"))
    return [(v, kind) for v, kind in found if v != canonical and normalize(v) == canonical]


def one_edit(a: str, b: str) -> bool:
    if len(a) == len(b):
        return one_substitution(a, b)
    short, long = sorted((a, b), key=len)
    return len(long) - len(short) == 1 and any(
        long[:i] + long[i + 1 :] == short for i in range(len(long))
    )


def different_pairs(canonical: Counter, min_count: int) -> list[tuple[str, str]]:
    """Pairs of attested canonical strings one edit apart, most frequent first."""
    candidates = [s for s, n in canonical.items() if n >= min_count and not {ZWJ, ZWNJ} & set(s)]
    neighbours: dict[str, list[str]] = defaultdict(list)
    for s in candidates:  # a string and its one-character deletions share keys with its edits
        neighbours[s].append(s)
        for i in range(len(s)):
            neighbours[s[:i] + "\0" + s[i + 1 :]].append(s)
            neighbours[s[:i] + s[i + 1 :]].append(s)
    pairs = set()
    for group in neighbours.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a != b and one_edit(a, b):
                    pairs.add(tuple(sorted((a, b))))
    return sorted(pairs, key=lambda p: (-min(canonical[p[0]], canonical[p[1]]), p))


def edit_kind(a: str, b: str) -> str:
    """What differs between two strings one edit apart, for spreading the B pairs.

    Source: Unicode 18.0 Khmer block layout (UnicodeData.txt): U+1780-17A2 consonants,
    U+17A3-17B3 independent vowels, U+17B6-17C5 dependent vowel signs, U+17C6-17D3 signs.
    """
    if len(a) != len(b):
        return "added-or-removed"
    i = next(i for i, (x, y) in enumerate(zip(a, b, strict=True)) if x != y)
    if i > 0 and a[i - 1] == COENG:
        return "subscript"
    ch = a[i]
    if "\u1780" <= ch <= "\u17a2":
        return "consonant"
    if "\u17b6" <= ch <= "\u17c5":
        return "vowel-sign"
    return "other"


def round_robin(groups: dict[str, list], limit: int) -> list:
    picked, queues = [], [list(items) for _, items in sorted(groups.items())]
    while len(picked) < limit and any(queues):
        for queue in queues:
            if queue and len(picked) < limit:
                picked.append(queue.pop(0))
    return picked


def drafts(texts: list[tuple[str, dict]], total: int, seed: int, min_count: int) -> list[dict]:
    rng = random.Random(seed)
    raw: Counter = Counter()
    canonical: Counter = Counter()
    provenance: dict[str, dict] = {}
    for text, where in texts:
        for run in runs(text):
            raw[run] += 1
            canonical[normalize(run)] += 1
            provenance.setdefault(run, where)
            provenance.setdefault(normalize(run), where)
    used: set[str] = set()
    records: list[dict] = []

    def add(kind: str, a: str, b: str, answer: str, transform: str, notes: str) -> None:
        used.update({normalize(a), normalize(b)})
        first, second = (a, b) if rng.random() < 0.5 else (b, a)
        where = provenance[a] if a in provenance else provenance[normalize(a)]
        record = {
            "task": TASK,
            "item_type": kind,
            "input": {"first": first, "second": second},
            "reference": answer,
            "source": where["source"],
            "license": where["license"],
            "retrieved": where["retrieved"],
            "transform": transform,
            "generated_by": "scripts/draft_encoding_items.py",
            "notes": notes,
            "first_codepoints": codepoints(first),
            "second_codepoints": codepoints(second),
            "verified": False,
        }
        if answer == "B" and provenance[b]["source"] != where["source"]:
            record["source_second"] = provenance[b]["source"]
        records.append(record)

    same_total = total // 2
    # Attested variants, spread over the normalization rules that produce them.
    by_rules: dict[str, list[str]] = defaultdict(list)
    for run, _count in sorted(raw.items(), key=lambda kv: (-kv[1], kv[0])):
        if normalize(run) != run and not {ZWJ, ZWNJ} & set(run):
            rules = sorted({r for c in normalize(run, report=True).changes for r in c.rules})
            by_rules[",".join(rules)].append(run)
    for run in round_robin(by_rules, same_total // 2):
        target = normalize(run)
        if target in used:
            continue
        rules = sorted({r for c in normalize(run, report=True).changes for r in c.rules})
        add(
            "same-attested",
            run,
            target,
            "A",
            "string found in the source in a non-canonical encoding, paired with its "
            "pheasa.normalize form",
            f"rules: {', '.join(rules)}; found {raw[run]} time(s) as typed; canonical form "
            f"found {raw[target]} time(s); check both look identical",
        )
    # Constructed variants of frequent canonical strings; at most a third via coeng da.
    da_limit, da_count = (same_total - len(records)) // 3, 0
    for target, _count in sorted(canonical.items(), key=lambda kv: (-kv[1], kv[0])):
        if len(records) >= same_total:
            break
        if target in used or raw[target] == 0 or {ZWJ, ZWNJ} & set(target):
            continue
        options = constructed_variants(target)
        if da_count >= da_limit:
            options = [o for o in options if o[1] != "coeng-da"]
        if not options:
            continue
        variant, how = options[rng.randrange(len(options))]
        da_count += how == "coeng-da"
        add(
            "same-constructed",
            variant,
            target,
            "A",
            f"canonical string from the source; second string built from it ({how}) and "
            "kept only because pheasa.normalize maps it back exactly",
            f"variant kind: {how}; check both look identical and that the typed order is "
            "one people produce",
        )
    # Different strings one edit apart, both attested in canonical form.
    by_edit: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for a, b in different_pairs(canonical, min_count):
        if raw[a] and raw[b]:
            by_edit[edit_kind(a, b)].append((a, b))
    for a, b in round_robin(by_edit, sum(len(v) for v in by_edit.values())):
        if len(records) >= total:
            break
        if a in used or b in used:
            continue
        add(
            "different-one-edit",
            a,
            b,
            "B",
            "two canonical strings found in the source that differ by one character",
            f"differs in: {edit_kind(a, b)}; found {raw[a]} and {raw[b]} time(s); check both "
            "are real words and clearly different",
        )
    for number, record in enumerate(records, start=1):
        record["id"] = f"{TASK}-v1d{number:04d}"
    return [{"id": r.pop("id"), **r} for r in records]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wikipedia", type=Path, help="folder of <pageid>.txt articles")
    parser.add_argument("--golden", type=Path, help="verified golden fixtures (JSONL)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=250)
    parser.add_argument("--min-count", type=int, default=2, help="for 'different' strings")
    parser.add_argument("--seed", type=int, default=20261123)
    args = parser.parse_args(argv)
    if "drafts" not in Path(args.out).parts:
        parser.error("drafts go to bench/drafts/ only; a person promotes them to bench/items/")
    if not args.wikipedia and not args.golden:
        parser.error("give --wikipedia, --golden or both")
    records = drafts(
        read_sources(args.wikipedia, args.golden), args.count, args.seed, args.min_count
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    kinds = Counter(r["item_type"] for r in records)
    print(f"wrote {len(records)} drafts to {out}: {dict(sorted(kinds.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
