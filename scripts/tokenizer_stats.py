"""How many tokens do public tokenizers spend on Khmer, before and after normalization?

    uv run --group research python scripts/tokenizer_stats.py PARALLEL \
        --tokenizer tiktoken:o200k_base --tokenizer hf:Qwen/Qwen2.5-0.5B \
        --tokenizer spm:path/to/model.spm [--json results.json]

PARALLEL is a TSV file (Khmer<TAB>English per line) or JSON Lines with "km" and "en"
fields; alternatively pass two line-aligned files with --km and --en. Both sides must be
the same sentences in the two languages. For each tokenizer this reports, on the
Khmer side both as given and after `pheasa.normalize`:

- tokens per character and per syllable (syllable = cluster, spec rule 2.1),
- the parity ratio: Khmer tokens / English tokens for the same sentences
  (1.0 means Khmer costs the same as English),
- how many sentences normalization changed, and the token count change on them,

and English tokens per whitespace word for reference. The `chars` tokenizer (one token
per character) needs no download and is used in tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from pheasa import NORMALIZATION_VERSION, normalize
from pheasa.normalize import _clusters

Encoder = Callable[[str], int]


def load_tokenizer(spec: str) -> Encoder:
    kind, _, name = spec.partition(":")
    if kind == "chars":
        return len
    if kind == "tiktoken":
        import tiktoken

        encoding = tiktoken.get_encoding(name)
        return lambda text: len(encoding.encode(text, disallowed_special=()))
    if kind == "hf":
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_pretrained(name)
        return lambda text: len(tokenizer.encode(text, add_special_tokens=False).ids)
    if kind == "spm":
        import sentencepiece

        model = sentencepiece.SentencePieceProcessor(model_file=name)
        return lambda text: len(model.encode(text))
    raise SystemExit(f"unknown tokenizer kind {kind!r} (use chars, tiktoken, hf or spm)")


def read_pairs(path: Path) -> list[tuple[str, str]]:
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if path.suffix == ".jsonl":
            record = json.loads(line)
            pairs.append((record["km"], record["en"]))
        else:
            km, en = line.split("\t")[:2]
            pairs.append((km, en))
    return pairs


def measure(encode: Encoder, pairs: list[tuple[str, str]]) -> dict:
    km_raw = km_norm = en = chars = syllables = words = 0
    changed = changed_raw = changed_norm = 0
    for km, english in pairs:
        normalized = normalize(km)
        raw_tokens, norm_tokens = encode(km), encode(normalized)
        km_raw += raw_tokens
        km_norm += norm_tokens
        en += encode(english)
        chars += len(km)
        syllables += sum(1 for _ in _clusters(normalized))
        words += len(english.split())
        if normalized != km:
            changed += 1
            changed_raw += raw_tokens
            changed_norm += norm_tokens
    return {
        "sentences": len(pairs),
        "km_tokens": km_raw,
        "km_tokens_normalized": km_norm,
        "en_tokens": en,
        "km_tokens_per_char": km_raw / chars,
        "km_tokens_per_syllable": km_norm / syllables,
        "en_tokens_per_word": en / words,
        "parity": km_raw / en,
        "parity_normalized": km_norm / en,
        "sentences_changed_by_normalize": changed,
        "tokens_on_changed_sentences": changed_raw,
        "tokens_on_changed_sentences_normalized": changed_norm,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("parallel", nargs="?", help="TSV or JSONL of Khmer/English pairs")
    parser.add_argument("--km", help="Khmer side as a text file, one sentence per line")
    parser.add_argument("--en", help="English side, line-aligned with --km")
    parser.add_argument("--tokenizer", action="append", required=True, dest="tokenizers")
    parser.add_argument("--json", help="also write the results as JSON")
    args = parser.parse_args(argv)

    if args.km and args.en:
        km = Path(args.km).read_text(encoding="utf-8").splitlines()
        en = Path(args.en).read_text(encoding="utf-8").splitlines()
        if len(km) != len(en):
            raise SystemExit(f"--km has {len(km)} lines but --en has {len(en)}")
        pairs = list(zip(km, en, strict=True))
    elif args.parallel:
        pairs = read_pairs(Path(args.parallel))
    else:
        raise SystemExit("give PARALLEL, or both --km and --en")
    results = {spec: measure(load_tokenizer(spec), pairs) for spec in args.tokenizers}
    print(f"{len(pairs)} sentence pairs; normalization version {NORMALIZATION_VERSION}\n")
    print("| tokenizer | km tok/char | km tok/syllable | en tok/word | parity | parity (norm.) |")
    print("|---|---|---|---|---|---|")
    for spec, r in results.items():
        print(
            f"| {spec} | {r['km_tokens_per_char']:.3f} | {r['km_tokens_per_syllable']:.3f} | "
            f"{r['en_tokens_per_word']:.3f} | {r['parity']:.2f} | {r['parity_normalized']:.2f} |"
        )
    if args.json:
        payload = {"normalization_version": NORMALIZATION_VERSION, "results": results}
        Path(args.json).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
