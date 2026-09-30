"""Draft encoding-equivalence items from a corpus (for a native speaker to pick from).

    uv run --group research python scripts/draft_encoding_pairs.py data/raw/fineweb2-khm \
        --pairs 10 --out bench/drafts/encoding-equivalence.jsonl

"Same" pairs (answer A): a syllable attested in the corpus both in canonical form and
in another encoding that `pheasa.normalize` maps to it. "Different" pairs (answer B):
two frequent canonical syllables that differ in exactly one character. Nothing is
invented; every string occurs in the corpus. Output is deterministic.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict

from lunar_probe import files, lines

from pheasa import normalize
from pheasa.normalize import _clusters

LICENSES = {
    "fineweb2-khm": ("ODC-By-1.0", "https://huggingface.co/datasets/HuggingFaceFW/fineweb-2")
}


def one_substitution(a: str, b: str) -> bool:
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b, strict=True)) == 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus")
    parser.add_argument("--pairs", type=int, default=10, help="pairs of each kind")
    parser.add_argument("--min-count", type=int, default=50)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    forms: dict[str, Counter] = defaultdict(Counter)
    for path in files([args.corpus]):
        for line in lines(path):
            text = unicodedata.normalize("NFC", line)
            for start, end in _clusters(text):
                forms[normalize(text[start:end])][text[start:end]] += 1

    same = []
    for canonical, raw in sorted(forms.items(), key=lambda kv: -sum(kv[1].values())):
        variants = [f for f, n in raw.most_common() if f != canonical and n >= 2]
        if raw[canonical] >= args.min_count and variants and len(canonical) >= 3:
            same.append((canonical, variants[0], raw[canonical], raw[variants[0]]))
    frequent = sorted(
        (c for c, raw in forms.items() if raw[c] >= args.min_count and len(c) >= 3),
        key=lambda c: -forms[c][c],
    )[:400]
    different = []
    for i, a in enumerate(frequent):
        for b in frequent[i + 1 :]:
            if one_substitution(a, b):
                different.append((a, b, forms[a][a], forms[b][b]))
                break

    name = args.corpus.rstrip("/").split("/")[-1]
    license_id, source = LICENSES.get(name, ("see corpus manifest", args.corpus))
    records = []
    picks = [("A", p) for p in same[: args.pairs]] + [("B", p) for p in different[: args.pairs]]
    for n, (answer, (a, b, count_a, count_b)) in enumerate(picks, start=1):
        first, second = (a, b) if n % 2 else (b, a)
        records.append(
            {
                "id": f"encoding-equivalence-d{n:03d}",
                "task": "encoding-equivalence",
                "input": {"first": first, "second": second},
                "reference": answer,
                "verified": False,
                "generated_by": "scripts/draft_encoding_pairs.py",
                "source": source,
                "license": license_id,
                "transform": "syllables counted in the corpus; both strings occur in it",
                "notes": f"counts in corpus: {count_a} and {count_b}; "
                + (
                    "normalize maps both to the same text"
                    if answer == "A"
                    else "one character differs"
                ),
                "first_codepoints": " ".join(f"{ord(c):04X}" for c in first),
                "second_codepoints": " ".join(f"{ord(c):04X}" for c in second),
            }
        )
    with open(args.out, "w", encoding="utf-8") as handle:
        for record in sorted(records, key=lambda r: r["id"]):
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"same pairs found: {len(same)}; different pairs found: {len(different)}")
    print(f"wrote {len(records)} drafts to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
