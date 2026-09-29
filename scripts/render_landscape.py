"""Render the tables in reports/landscape.md from reports/landscape.jsonl.

    uv run python scripts/render_landscape.py [--check]

Replaces the text between `<!-- tables:start -->` and `<!-- tables:end -->`. With
`--check`, exits 1 if the file is not up to date (used by `make check`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DATA = Path("reports/landscape.jsonl")
REPORT = Path("reports/landscape.md")
START, END = "<!-- tables:start -->", "<!-- tables:end -->"
CATEGORIES = [
    ("benchmark", "Benchmarks"),
    ("dataset", "Datasets"),
    ("model", "Models"),
    ("tool", "Tools"),
]
GROUPS = [
    ("Permissive", {"MIT", "Apache-2.0", "CC-BY-4.0", "ODC-By-1.0", "Unicode-3.0"}),
    ("Share-alike or copyleft", {"CC-BY-SA-4.0", "CC-BY-SA-3.0", "GPL-3.0", "LGPL-2.1"}),
    ("Non-commercial", {"CC-BY-NC-4.0", "CC-BY-NC-SA-4.0"}),
    ("Unknown (no license found)", {"unknown"}),
]


def group(license_id: str) -> str:
    for name, members in GROUPS:
        if license_id in members:
            return name
    lowered = license_id.lower()
    if "cc0" in lowered:
        return "Permissive"
    if "sa" in lowered.replace("seallms", "") and "nc" not in lowered:
        return "Share-alike or copyleft"
    return "Custom, mixed or by agreement"


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(rows: list[dict]) -> str:
    counts = Counter(group(r["license_spdx"]) for r in rows)
    parts = [
        f"{len(rows)} resources. License groups (each checked at the source on the date in "
        "`license_check`):",
        "",
        "| License group | Resources |",
        "|---|---|",
        *(
            f"| {name} | {counts[name]} |"
            for name, _ in [*GROUPS, ("Custom, mixed or by agreement", 0)]
        ),
    ]
    for key, title in CATEGORIES:
        selected = [r for r in rows if r["category"] == key]
        parts += [
            "",
            f"### {title} ({len(selected)})",
            "",
            "| Name | Purpose | Khmer | Size | License | Access | Updated | Notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in selected:
            coverage = "only" if r["khmer_coverage"] == "khmer-only" else "multilingual"
            note = r["quality_note"]
            if r["confidence"] != "high":
                note += f" (confidence {r['confidence']}: {r['confidence_reason']})"
            parts.append(
                f"| [{cell(r['name'])}]({r['url']}) | {cell(r['purpose'])} | {coverage} | "
                f"{cell(r['size'])} | {cell(r['license_spdx'])} | {r['access']} | "
                f"{r['last_update']} | {cell(note)} |"
            )
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not REPORT.exists():
        return 0
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    text = REPORT.read_text(encoding="utf-8")
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    updated = f"{head}{START}\n{render(rows)}\n{END}{tail}"
    if args.check:
        if updated != text:
            print(
                "reports/landscape.md is out of date: run scripts/render_landscape.py",
                file=sys.stderr,
            )
            return 1
        return 0
    REPORT.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
