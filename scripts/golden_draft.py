"""Turn lines of real text into draft golden fixtures for a native speaker to verify.

    uv run python scripts/golden_draft.py INPUT.txt --source URL --license LICENSE \
        --retrieved 2026-09-30 --transform "line split; handles removed" \
        --out tests/golden/drafts/NAME.jsonl

Each non-empty line becomes one draft with `expected` set to Pheasa's current output,
plus the rules that fired and the code points of both sides to help the review. Drafts
have empty `verified_by` and `verified_at`. To promote a draft, the verifier checks
`expected`, fills in both fields and moves the line to tests/golden/normalization.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_golden import PERSONAL

from pheasa import normalize


def codepoints(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text)


def next_id(root: Path) -> int:
    highest = 0
    for path in (root / "tests" / "golden").glob("**/*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                highest = max(highest, int(json.loads(line)["id"].removeprefix("G-")))
    return highest + 1


def draft_record(line: str, fixture_id: int, options: dict, provenance: dict) -> dict:
    """One unverified draft: Pheasa's current output plus review aids."""
    report = normalize(line, report=True, **options)
    return {
        "id": f"G-{fixture_id:04d}",
        "input": line,
        "expected": report.text,
        "options": options,
        **provenance,
        "verified_by": "",
        "verified_at": "",
        "rules": sorted({rule for change in report.changes for rule in change.rules}),
        "issues": [issue.code for issue in report.issues],
        "input_codepoints": codepoints(line),
        "expected_codepoints": codepoints(report.text),
    }


def write_drafts(drafts: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        for draft in drafts:
            handle.write(json.dumps(draft, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input")
    parser.add_argument("--source", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--retrieved", required=True, help="ISO date")
    parser.add_argument("--transform", required=True)
    parser.add_argument("--options", default="{}", help="normalize options as JSON")
    parser.add_argument("--changed-only", action="store_true", help="skip unchanged lines")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    options = json.loads(args.options)
    number = next_id(Path.cwd())
    drafts, flagged = [], 0
    provenance = {
        "source": args.source,
        "license": args.license,
        "retrieved": args.retrieved,
        "transform": args.transform,
    }
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if PERSONAL.search(line):
            flagged += 1
            print(f"skipped (handle or email): {line[:40]!r}", file=sys.stderr)
            continue
        draft = draft_record(line, number, options, provenance)
        if args.changed_only and draft["expected"] == line:
            continue
        drafts.append(draft)
        number += 1
    out = Path(args.out)
    write_drafts(drafts, out)
    print(f"wrote {len(drafts)} drafts to {out}" + (f"; skipped {flagged}" if flagged else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
