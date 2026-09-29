"""Count syllables that occur under more than one byte sequence in a text sample.

    uv run python scripts/encoding_variants.py [--raw data/raw/wikipedia-km] [--top 10]

Every syllable cluster (spec rule 2.1) in the NFC text is grouped by its normalized
form. A syllable "has variants" if the sample contains it under two or more different
code point sequences. Prints totals and the most frequent variant sets as code points.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from pheasa import normalize
from pheasa.normalize import _clusters


def codepoints(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", default="data/raw/wikipedia-km")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)

    forms: dict[str, Counter] = defaultdict(Counter)
    tokens = 0
    for path in sorted(Path(args.raw).glob("*.txt")):
        text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
        for start, end in _clusters(text):
            cluster = text[start:end]
            forms[normalize(cluster)][cluster] += 1
            tokens += 1
    variant = {norm: raw for norm, raw in forms.items() if len(raw) > 1}
    affected = sum(sum(raw.values()) for raw in variant.values())
    noncanonical = sum(n for norm, raw in forms.items() for form, n in raw.items() if form != norm)
    print(f"syllable tokens: {tokens}; distinct syllables: {len(forms)}")
    print(f"syllables seen in 2+ encodings: {len(variant)}; their tokens: {affected}")
    print(f"tokens not in canonical form: {noncanonical} ({100 * noncanonical / tokens:.2f}%)")
    ranked = sorted(variant.items(), key=lambda item: -sum(item[1].values()))
    for norm, raw in ranked[: args.top]:
        parts = "; ".join(f"{codepoints(form)} x{n}" for form, n in raw.most_common())
        print(f"{codepoints(norm)}: {parts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
