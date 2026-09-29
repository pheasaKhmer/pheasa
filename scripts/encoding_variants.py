"""Count syllables that occur under more than one byte sequence in a text sample.

    uv run python scripts/encoding_variants.py [CORPUS ...] [--top 10]

CORPUS is a file or directory in any format scripts/lunar_probe.py reads (plain text,
compressed, JSON Lines or parquet); the default is data/raw/wikipedia-km.

Every syllable cluster (spec rule 2.1) in the NFC text is grouped by its normalized
form. A syllable "has variants" if the sample contains it under two or more different
code point sequences. Prints totals and the most frequent variant sets as code points.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import Counter, defaultdict

from lunar_probe import files, lines

from pheasa import normalize
from pheasa.normalize import _clusters


def codepoints(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", nargs="*", default=["data/raw/wikipedia-km"])
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)

    forms: dict[str, Counter] = defaultdict(Counter)
    tokens = 0
    for path in files(args.corpus):
        if path.name.endswith("sample.jsonl"):
            continue  # probe output, not corpus
        for line in lines(path):
            text = unicodedata.normalize("NFC", line)
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
