"""Write a local HTML page for picking benchmark draft items and Khmer prompts.

    uv run python scripts/review_items.py bench/drafts --html review/pick.html

For every draft item: its input fields, the proposed reference, notes and source, and
keep / fix / drop buttons with a note box. For every draft Khmer prompt: the English
prompt next to it and keep / fix buttons. The page works without scripts; where scripts
run, it builds a summary to copy back. It sends nothing anywhere.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import tomllib
from pathlib import Path

STYLE = """
body { font-family: system-ui, sans-serif; margin: 16px; color: #111; background: #fff; }
h2 { margin-top: 2em; border-bottom: 2px solid #333; }
.item { border: 1px solid #ccc; border-radius: 6px; padding: 10px; margin: 10px 0; }
.item:has(input[value=keep]:checked) { background: #eef9ee; }
.item:has(input[value=fix]:checked) { background: #fff7e0; }
.item:has(input[value=drop]:checked) { background: #fdeeee; }
.k { font-size: 20px; line-height: 1.9; white-space: pre-wrap; }
.field { color: #555; font-size: 13px; }
.ref { font-weight: bold; }
label { margin-right: 14px; font-size: 16px; cursor: pointer; }
textarea { width: 100%; height: 3em; }
code { font-size: 12px; color: #444; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 700px) { .cols { grid-template-columns: 1fr; } }
"""
SCRIPT = """
function update() {
  const out = {keep: [], fix: {}, drop: []};
  for (const box of document.querySelectorAll('.item')) {
    const picked = box.querySelector('input:checked');
    if (!picked) continue;
    const note = box.querySelector('textarea').value.trim();
    if (picked.value === 'fix') out.fix[box.id] = note; else out[picked.value].push(box.id);
  }
  document.getElementById('summary').value = JSON.stringify(out);
}
document.addEventListener('change', update);
document.addEventListener('input', update);
"""


def verdicts(item_id: str, choices: tuple[str, ...]) -> str:
    buttons = "".join(
        f'<label><input type="radio" name="{item_id}" value="{c}"> {c}</label>' for c in choices
    )
    return f'<div>{buttons}</div><textarea placeholder="what to fix (optional)"></textarea>'


def field(name: str, value: object) -> str:
    label, text = html.escape(name), html.escape(str(value))
    return f'<div class="field">{label}</div><div class="k">{text}</div>'


def item_box(item: dict) -> str:
    refs = item["reference"] if isinstance(item["reference"], list) else [item["reference"]]
    parts = [f'<div class="item" id="{html.escape(item["id"])}"><b>{html.escape(item["id"])}</b>']
    parts += [field(k, v) for k, v in item["input"].items()]
    parts += [
        f'<div class="field">answer</div><div class="k ref">{html.escape(" | ".join(refs))}</div>'
    ]
    note = item.get("notes", "") + "; " + item.get("transform", "")
    source = item.get("source", "")
    link = f' · <a href="{html.escape(source)}">source</a>' if source.startswith("http") else ""
    parts += [
        f"<p><code>{html.escape(note)}</code>{link}</p>",
        verdicts(item["id"], ("keep", "fix", "drop")),
        "</div>",
    ]
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts")
    parser.add_argument("--tasks", default="bench/tasks")
    parser.add_argument("--html", required=True)
    args = parser.parse_args(argv)
    drafts = Path(args.drafts)
    page = [
        "<!doctype html><html lang=km><meta charset=utf-8>",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Pilot item picker</title><style>{STYLE}</style>",
        "<h1>Pilot benchmark: pick draft items and prompts</h1>",
        "<p>Everything here is an unverified draft. For each item choose <b>keep</b> (correct"
        " as shown), <b>fix</b> (useful but needs a change: say what) or <b>drop</b>. About 12"
        " to 15 kept items per task is enough for the pilot. Then copy the summary at the"
        " bottom. If the summary box stays empty, send the IDs to keep and your fix notes.</p>",
    ]
    prompts_path = drafts / "prompts-km.toml"
    if prompts_path.exists():
        khmer = tomllib.loads(prompts_path.read_text(encoding="utf-8"))
        page.append("<h2>Khmer prompts</h2>")
        for name, entry in khmer.items():
            task = tomllib.loads((Path(args.tasks) / f"{name}.toml").read_text(encoding="utf-8"))
            box_id = f"prompt-{name}"
            page.append(
                f'<div class="item" id="{box_id}"><b>{html.escape(name)}</b><div class="cols">'
                f"<div>{field('English (current)', task['prompts']['en'])}</div>"
                f"<div>{field('Khmer (draft)', entry['km'])}</div></div>"
                f"{verdicts(box_id, ('keep', 'fix'))}</div>"
            )
    for path in sorted(drafts.glob("*.jsonl")):
        items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        page.append(f"<h2>{html.escape(path.stem)} ({len(items)} drafts)</h2>")
        page += [item_box(item) for item in items]
    page += [
        "<h2>Summary to copy back</h2><textarea id=summary readonly style='height:8em'></textarea>",
        f"<script>{SCRIPT}</script></html>",
    ]
    Path(args.html).write_text("\n".join(page), encoding="utf-8")
    print(f"wrote {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
