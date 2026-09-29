"""Count legacy lunar-date sequences (D-009) in a text corpus and sample them for review.

    uv run python scripts/lunar_probe.py CORPUS [CORPUS ...] [--sample 100 --out FILE]

CORPUS may be a file or a directory. Files may be plain text, .gz, .bz2 or .xz, and
.jsonl files are read from their "text" field. Text is streamed line by line, so the
corpus never has to fit in memory. Prints counts only; `--out` writes a deterministic
sample of matches with 30 characters of context on each side, as JSON Lines, for a
native speaker to classify as lunar date or typing/OCR artifact.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
import lzma
import random
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from pheasa.validate import _LUNAR

OPENERS = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}
CONTEXT = 30


def files(paths: list[str]) -> Iterator[Path]:
    for name in paths:
        path = Path(name)
        yield from sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]


def lines(path: Path) -> Iterator[str]:
    opener = OPENERS.get(path.suffix, open)
    is_jsonl = ".jsonl" in path.suffixes
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if is_jsonl:
                if line.strip():
                    yield from json.loads(line).get("text", "").splitlines()
            else:
                yield line


def codepoints(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", nargs="+")
    parser.add_argument("--sample", type=int, default=100)
    parser.add_argument("--out", help="write a sample of matches with context (JSON Lines)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    forms, sample = Counter(), []
    matches = characters = 0
    for path in files(args.corpus):
        for number, line in enumerate(lines(path), start=1):
            characters += len(line)
            for match in _LUNAR.finditer(line):
                matches += 1
                forms[codepoints(match.group())] += 1
                record = {
                    "file": str(path),
                    "line": number,
                    "match": codepoints(match.group()),
                    "before": line[max(0, match.start() - CONTEXT) : match.start()],
                    "text": match.group(),
                    "after": line[match.end() : match.end() + CONTEXT].rstrip("\n"),
                    "label": "",
                }
                # Reservoir sampling keeps the sample uniform and deterministic.
                if len(sample) < args.sample:
                    sample.append(record)
                elif (k := rng.randrange(matches)) < args.sample:
                    sample[k] = record
    rate = 1e6 * matches / characters if characters else 0.0
    print(f"characters: {characters}; matches: {matches} ({rate:.2f} per million characters)")
    for form, count in forms.most_common(20):
        print(f"  {form}: {count}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            for record in sample:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"wrote {len(sample)} samples to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
