"""Write an HTML page for a native speaker to review golden-fixture drafts.

    uv run python scripts/review_drafts.py tests/golden/drafts/NAME.jsonl --html review.html

For each draft the page shows the input and Pheasa's output as text (in the browser's
Khmer font), the code points of each changed span, the rules that fired and the source.
The reviewer marks each row correct or wrong; the page then shows a summary line to copy
back, such as {"correct": ["G-0001"], "wrong": ["G-0002"]}. The page runs locally and
sends nothing anywhere.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from pheasa import normalize

STYLE = """
body { font-family: system-ui, sans-serif; margin: 16px; color: #111; background: #fff; }
table { border-collapse: collapse; width: 100%; }
td, th { border-bottom: 1px solid #ddd; padding: 8px; vertical-align: top; text-align: left; }
.khmer { font-size: 22px; line-height: 1.9; }
code { font-size: 12px; color: #444; }
.change { color: #a40; }
tr.correct { background: #eef9ee; } tr.wrong { background: #fdeeee; }
#summary { width: 100%; height: 4em; font-family: monospace; }
"""
SCRIPT = """
const marks = {};
function mark(id, verdict) {
  marks[id] = verdict;
  document.getElementById(id).className = verdict;
  const out = {correct: [], wrong: []};
  for (const [k, v] of Object.entries(marks)) out[v].push(k);
  document.getElementById('summary').value = JSON.stringify(out);
}
"""


def codepoints(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text) or "(nothing)"


def row(draft: dict) -> str:
    report = normalize(draft["input"], report=True, **draft.get("options", {}))
    changes = (
        "<br>".join(
            f'<code class="change">{codepoints(c.before)} → {codepoints(c.after)}</code> '
            f"<code>({', '.join(c.rules)})</code>"
            for c in report.changes
        )
        or "<code>no change</code>"
    )
    fid = html.escape(draft["id"])
    rules = html.escape(", ".join(draft["rules"]))
    return (
        f'<tr id="{fid}"><td><b>{fid}</b><br><code>{rules}</code></td>'
        f'<td class="khmer">{html.escape(draft["input"])}</td>'
        f'<td class="khmer">{html.escape(report.text)}</td>'
        f'<td>{changes}<br><a href="{html.escape(draft["source"])}">source</a></td>'
        f"<td><button onclick=\"mark('{fid}','correct')\">correct</button> "
        f"<button onclick=\"mark('{fid}','wrong')\">wrong</button></td></tr>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts")
    parser.add_argument("--html", required=True)
    args = parser.parse_args(argv)
    drafts = [
        json.loads(line) for line in Path(args.drafts).read_text("utf-8").splitlines() if line
    ]
    page = [
        "<!doctype html><html lang=km><meta charset=utf-8>",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Fixture review</title><style>{STYLE}</style>",
        f"<h1>Golden fixture review: {len(drafts)} drafts</h1>",
        "<p>Is the output column the correct form of the input? Mark each row, then copy the "
        "summary at the bottom. Text is from Khmer Wikipedia (CC BY-SA 4.0); the output is "
        "Pheasa's, unverified.</p>",
        "<table><tr><th>ID / rules</th><th>Input</th><th>Output</th><th>What changed</th>"
        "<th>Verdict</th></tr>",
        *(row(draft) for draft in drafts),
        "</table><h2>Summary to copy back</h2><textarea id=summary readonly></textarea>",
        f"<script>{SCRIPT}</script></html>",
    ]
    Path(args.html).write_text("\n".join(page), encoding="utf-8")
    print(f"wrote {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
