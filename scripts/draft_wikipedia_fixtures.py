"""Pick golden-fixture drafts from the fetched Khmer Wikipedia sample.

    uv run python scripts/draft_wikipedia_fixtures.py

Splits each article into sentences (at newlines and at U+17D4 KHAN / U+17D5 BARIYOOSAN),
keeps sentences that Pheasa changes, spreading the picks across the rule combinations
seen, and adds a few unchanged sentences as controls. Selection is deterministic.
Prints counts only. Writes tests/golden/drafts/wikipedia-km.jsonl (replacing it).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from golden_draft import PERSONAL, draft_record, next_id, write_drafts

from pheasa import normalize

SENTENCE_END = re.compile(r"(?<=[។៕])|\n")
KHMER = re.compile(r"[ក-៿]")


def sentences(text: str) -> list[str]:
    parts = (part.strip() for part in SENTENCE_END.split(text))
    return [p for p in parts if 8 <= len(p) <= 160 and KHMER.search(p) and not PERSONAL.search(p)]


def stable_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default="data/wikipedia-km/manifest.jsonl")
    parser.add_argument("--raw", default="data/raw/wikipedia-km")
    parser.add_argument("--max", type=int, default=60, help="changed sentences to draft")
    parser.add_argument("--controls", type=int, default=10, help="unchanged sentences to draft")
    parser.add_argument("--out", default="tests/golden/drafts/wikipedia-km.jsonl")
    args = parser.parse_args(argv)

    by_rules: dict[tuple, list[tuple[str, dict]]] = defaultdict(list)
    unchanged: list[tuple[str, dict]] = []
    rule_counts, issue_counts, seen = Counter(), Counter(), set()
    total = 0
    for line in Path(args.manifest).read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        path = Path(args.raw) / f"{record['pageid']}.txt"
        if not path.exists():
            continue
        provenance = {
            "source": record["source"],
            "license": record["license"],
            "retrieved": record["retrieved"],
            "transform": record["transform"] + "; one sentence (split at newline and khan)",
        }
        for sentence in sentences(path.read_text(encoding="utf-8")):
            if sentence in seen:
                continue
            seen.add(sentence)
            total += 1
            report = normalize(sentence, report=True)
            rules = tuple(sorted({r for change in report.changes for r in change.rules}))
            rule_counts.update(rules)
            issue_counts.update({issue.code for issue in report.issues})
            if rules:
                by_rules[rules].append((sentence, provenance))
            elif not report.issues:
                unchanged.append((sentence, provenance))

    # Round-robin over rule combinations so rare rules are represented.
    groups = [
        sorted(group, key=lambda item: stable_key(item[0])) for _, group in sorted(by_rules.items())
    ]
    picked: list[tuple[str, dict]] = []
    while len(picked) < args.max and any(groups):
        for group in groups:
            if group and len(picked) < args.max:
                picked.append(group.pop(0))
    picked += sorted(unchanged, key=lambda item: stable_key(item[0]))[: args.controls]

    out = Path(args.out)
    out.unlink(missing_ok=True)
    number = next_id(Path.cwd())
    drafts = [draft_record(s, number + k, {}, prov) for k, (s, prov) in enumerate(picked)]
    write_drafts(drafts, out)

    changed = sum(len(group) for group in by_rules.values())
    print(f"sentences: {total}; changed: {changed}; clean and unchanged: {len(unchanged)}")
    print("rules fired (sentences):", dict(sorted(rule_counts.items())))
    print("issues (sentences):", dict(sorted(issue_counts.items())))
    print(f"wrote {len(drafts)} drafts to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
