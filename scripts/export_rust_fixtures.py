"""Write the parity cases that hold the Rust port of the normalizer to Python (D-015).

The file, rust/tests/fixtures/parity.tsv, lists inputs with Python's output for each:
every input of the golden fixtures (tests/golden/*.jsonl), every Khmer and test-alphabet
character in a few contexts, and generated text built from the alphabets and tokens of
the property tests (tests/test_normalize.py, tests/test_options.py) with fixed seeds.
For each input it stores the output with default options, and the output under every
other combination of the options whose characters occur in the input, if it differs.
The Rust tests (rust/tests/parity.rs) require the same output for every case.

    uv run python scripts/export_rust_fixtures.py           # rewrite the file
    uv run python scripts/export_rust_fixtures.py --check   # fail if it is out of date

Generation uses only `random.Random` methods whose results are the same on every
supported Python, and characters whose NFC is the same in every Unicode version since
3.2, so the file does not depend on the Python version.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
import test_normalize as tn
import test_options as to

from pheasa import NORMALIZATION_VERSION, normalize

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "rust" / "tests" / "fixtures" / "parity.tsv"
SEED = "pheasa-rust-parity"

ZWSP_VALUES = ("keep", "strip", "space")
DIGIT_VALUES = ("keep", "khmer", "ascii")
DEFAULTS = ("keep", "keep", False, False)
ASCII_DIGITS = frozenset("0123456789")
KHMER_DIGITS = frozenset(to.KHMER_DIGITS)
DEPRECATED = frozenset(to.DEPRECATED)
COENG_DA = frozenset((tn.COENG, "\u178a"))

# Characters of other scripts that NFC decomposes, composes or reorders, spread over
# many combining classes, plus a few Khmer characters to mix with them. Every non-Khmer
# character here is assigned in Unicode 3.2, so NFC treats it the same in every version.
SCRIPT_CHARS = [
    # Latin: base letters, combining marks (ccc 202-240), precomposed letters, singletons
    *"aeouAE",
    *"\u0300\u0301\u0302\u0303\u0306\u0308\u031b\u0323\u0327\u0328\u0340\u0344\u0345",
    *"\u00c5\u00e9\u1ea0\u212b\u2126\u01fa",
    # Greek
    *"\u03b1\u03c9\u0313\u0342\u1f00",
    # Hangul jamo and syllables (algorithmic composition)
    *"\u1100\u1161\u11a8\uac00\uac01",
    # Devanagari: nukta (ccc 7), virama (ccc 9), a composition exclusion (0958)
    *"\u0915\u0928\u0929\u093c\u094d\u0958",
    # Hebrew points (ccc 10-21) and a presentation form that NFC decomposes
    *"\u05d0\u05b0\u05b7\u05bc\ufb2c",
    # Thai (ccc 103, 107), Tibetan (ccc 129, 130, decompositions), Arabic (ccc 220, 230)
    *"\u0e01\u0e38\u0e48\u0f40\u0f71\u0f72\u0f73\u0f80\u0627\u0653\u0654\u0655",
    # Musical symbols in the supplementary planes (ccc 1, 216, 226; excluded composites)
    "\U0001d15e",
    "\U0001d165",
    "\U0001d167",
    "\U0001d16d",
    # CJK compatibility ideographs (singletons)
    "\uf900",
    "\U0002f800",
    # Joiners, a variation selector, the combining grapheme joiner, a symbol
    *"\u200c\u200d\ufe0f\u034f\u2764",
    # Khmer: bases, COENG (ccc 9), ATTHACAN (ccc 230), vowels, robat, a shifter
    *"\u1780\u1798\u17d2\u17dd\u17b6\u17bb\u17c1\u17cc\u17c9",
]

Sample = Callable[[random.Random], str]


def size(rng: random.Random, max_size: int) -> int:
    """A text length up to `max_size`. Like hypothesis, it favors short texts."""
    return min(rng.randrange(max_size + 1), rng.randrange(max_size + 1))


def text_of(alphabet: list[str], max_size: int = 24) -> Sample:
    """Up to `max_size` characters from `alphabet`, like `st.lists(...).map("".join)`."""
    return lambda rng: "".join(rng.choice(alphabet) for _ in range(size(rng, max_size)))


TOKEN_GROUPS = [*tn.TOKEN_CHOICES.values(), *([token] for token in tn.OTHER_TOKENS)]


def wellformed_cluster(rng: random.Random) -> str:
    """A base and up to six tokens in any order (`wellformed_cluster`)."""
    tokens = (rng.choice(rng.choice(TOKEN_GROUPS)) for _ in range(rng.randrange(7)))
    return rng.choice(tn.BASES) + "".join(tokens)


def wellformed_text(rng: random.Random) -> str:
    """Up to six clusters and separators (`wellformed_text`)."""
    parts = (
        wellformed_cluster(rng) if rng.randrange(2) else rng.choice(tn.SEPARATORS)
        for _ in range(rng.randrange(7))
    )
    return "".join(parts)


def u_cluster(rng: random.Random) -> str:
    """A cluster where rule 3.6 may turn -u into a shifter (`u_cluster`)."""
    coengs = (rng.choice(tn.TOKEN_CHOICES["coeng"]) for _ in range(rng.randrange(4)))
    rest = (rng.choice(tn.U_FOLLOWERS) for _ in range(rng.randrange(3)))
    robat = rng.choice(["", tn.ROBAT])
    return rng.choice(tn.BASES) + robat + "".join(coengs) + tn.U + "".join(rest)


def u_text(rng: random.Random) -> str:
    return " ".join(u_cluster(rng) for _ in range(rng.randrange(1, 4)))


def option_text(rng: random.Random) -> str:
    """Text with ASCII digits and extra ZWSP (`option_text`)."""
    return text_of(to.OPTION_ALPHABET)(rng) if rng.randrange(2) else wellformed_text(rng)


def typing_order(rng: random.Random) -> str:
    """A base and one token for each of some sort keys, shuffled (the typing-order test)."""
    keys = [key for key in sorted(tn.TOKEN_CHOICES) if rng.randrange(2)]
    tokens = [rng.choice(tn.TOKEN_CHOICES[key]) for key in keys]
    rng.shuffle(tokens)
    return rng.choice(tn.BASES) + "".join(tokens)


def script_text(rng: random.Random) -> str:
    """Other scripts mixed with Khmer clusters, for NFC and rule 2.3."""
    parts = (
        wellformed_cluster(rng) if rng.randrange(5) == 0 else rng.choice(SCRIPT_CHARS)
        for _ in range(size(rng, 24))
    )
    return "".join(parts)


def bom_text(rng: random.Random) -> str:
    """A run of byte order marks before other generated text (rule 1.1)."""
    rest = rng.choice([text_of(tn.KHMER_TEXT_ALPHABET), text_of(tn.MIXED_ALPHABET), u_text])
    return tn.BOM * rng.randrange(1, 4) + rest(rng)


# Generated sections: code, description, number of distinct inputs, generator.
GENERATED: list[tuple[str, str, int, Sample]] = [
    ("k", "Khmer text (khmer_text)", 5000, text_of(tn.KHMER_TEXT_ALPHABET)),
    ("m", "Khmer mixed with NFC probes and BOM (mixed_text)", 3000, text_of(tn.MIXED_ALPHABET)),
    ("w", "clusters with marks in any order (wellformed_text)", 4000, wellformed_text),
    ("u", "-u clusters for rule 3.6 (u_cluster)", 3000, u_text),
    ("o", "text for the options (option_text)", 3000, option_text),
    ("t", "one token per sort key, shuffled", 2000, typing_order),
    ("s", "other scripts mixed with Khmer", 2000, script_text),
    ("b", "leading byte order marks", 500, bom_text),
]


def golden_inputs() -> list[str]:
    return [
        json.loads(line)["input"]
        for path in sorted((ROOT / "tests" / "golden").glob("*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def character_inputs() -> list[str]:
    """Every Khmer and test-alphabet character alone and in a few contexts."""
    alphabet = {*tn.KHMER, *tn.MIXED_ALPHABET, *to.OPTION_ALPHABET, *SCRIPT_CHARS}
    contexts = [
        "{}",
        "\u1780{}",  # after a base
        "\u1780{}\u17b6\u17d2\u1781",  # inside a cluster, before marks
        "\u1780\u17d2{}",  # after a COENG
        "\u1780\u17dd\u17b6{}",  # after a cluster that ends in ATTHACAN (ccc 230)
        "\u1780\u17b6\u17d2{}",  # after a dangling COENG (ccc 9)
    ]
    return [context.format(ch) for ch in sorted(alphabet) for context in contexts]


def option_values(text: str) -> list[Iterable[object]]:
    """The values of each option that can change the output for `text`.

    Stage 4 substitutes single characters, and rule 3.8 needs U+17D2 and U+178A, so an
    option whose characters do not occur in the input has no effect.
    """
    chars = set(text)
    digits = ["keep"]
    if chars & ASCII_DIGITS:
        digits.append("khmer")
    if chars & KHMER_DIGITS:
        digits.append("ascii")
    return [
        ZWSP_VALUES if tn.ZWSP in chars else ZWSP_VALUES[:1],
        digits,
        (False, True) if chars & DEPRECATED else (False,),
        (False, True) if chars >= COENG_DA else (False,),
    ]


def run(text: str, zwsp: str, digits: str, fold_deprecated: bool, preserve: bool) -> str:
    return normalize(
        text,
        zwsp=zwsp,
        digits=digits,
        fold_deprecated=fold_deprecated,
        preserve_coeng_da=preserve,
    )


def option_code(zwsp: str, digits: str, fold_deprecated: bool, preserve: bool) -> str:
    return (
        f"{ZWSP_VALUES.index(zwsp)}{DIGIT_VALUES.index(digits)}"
        f"{int(fold_deprecated)}{int(preserve)}"
    )


def escape(text: str) -> str:
    """Escape `text` for one tab-separated field. Control and line-separator characters
    become `\\t`, `\\n`, `\\r` or `\\u{XXXX}`, and a lone "=" becomes `\\=`."""
    out = []
    for ch in text:
        cp = ord(ch)
        if ch in "\\\t\n\r":
            out.append({"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}[ch])
        elif cp < 0x20 or 0x7F <= cp < 0xA0 or cp in (0x2028, 0x2029):
            out.append(f"\\u{{{cp:04X}}}")
        else:
            out.append(ch)
    field = "".join(out)
    return "\\=" if field == "=" else field


def case_line(section: str, text: str) -> str:
    def output(result: str) -> str:
        return "=" if result == text else escape(result)

    default = normalize(text)
    fields = [section, escape(text), output(default)]
    for combo in itertools.product(*option_values(text)):
        if combo != DEFAULTS and (result := run(text, *combo)) != default:
            fields += (option_code(*combo), output(result))
    return "\t".join(fields)


def all_combinations_agree(text: str) -> bool:
    """Do options that `option_values` leaves out really make no difference for `text`?"""
    values = option_values(text)
    for combo in itertools.product(ZWSP_VALUES, DIGIT_VALUES, (False, True), (False, True)):
        projected = tuple(
            value if value in allowed else default
            for value, allowed, default in zip(combo, values, DEFAULTS, strict=True)
        )
        if run(text, *combo) != run(text, *projected):
            return False
    return True


def sections() -> list[tuple[str, str, list[str]]]:
    seen: set[str] = set()

    def distinct(texts: Iterable[str]) -> list[str]:
        kept = [text for text in dict.fromkeys(texts) if text not in seen]
        seen.update(kept)
        return kept

    result = [
        ("g", "golden fixtures (tests/golden)", distinct(golden_inputs())),
        ("c", "single characters in context", distinct(character_inputs())),
    ]
    for code, description, count, sample in GENERATED:
        rng = random.Random(f"{SEED}-{code}")
        texts: list[str] = []
        for _ in range(count * 50):
            texts += distinct([sample(rng)])
            if len(texts) == count:
                break
        else:
            raise RuntimeError(f"section {code}: fewer than {count} distinct inputs")
        result.append((code, description, texts))
    return result


def render() -> str:
    for ch in SCRIPT_CHARS:
        if not "\u1780" <= ch <= "\u17ff" and unicodedata.ucd_3_2_0.category(ch) == "Cn":
            raise RuntimeError(f"U+{ord(ch):04X} is not assigned in Unicode 3.2")
    parts = sections()
    total = sum(len(texts) for _, _, texts in parts)
    header = [
        "# Parity cases for the Rust port of pheasa's normalizer (rust/, D-015).",
        "# Written by scripts/export_rust_fixtures.py from the Python implementation;",
        "# do not edit.",
        f"# normalization_version: {NORMALIZATION_VERSION}",
        "#",
        "# One case per line, tab-separated: section, input, output with default options,",
        "# then an option code and an output for every other combination of the options",
        "# whose characters occur in the input, when that output differs from the default.",
        "# Other options cannot change the output. The option code has four",
        "# digits: zwsp (0 keep, 1 strip, 2 space), digits (0 keep, 1 khmer, 2 ascii),",
        "# fold_deprecated and preserve_coeng_da (0 false, 1 true). An output of = is",
        "# the input unchanged. Escapes: \\\\ \\t \\n \\r \\= and \\u{XXXX}.",
        "#",
        f"# {total} inputs:",
        *(f"#   {code} {len(texts):>5}  {description}" for code, description, texts in parts),
    ]
    lines = [case_line(code, text) for code, _, texts in parts for text in texts]
    # Spot-check that options whose characters do not occur cannot change the output.
    inputs = [text for _, _, texts in parts for text in texts]
    for text in inputs[::25]:
        if not all_combinations_agree(text):
            raise RuntimeError(f"an option not in option_values changes {text!r}")
    return "\n".join([*header, *lines]) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the file is out of date")
    args = parser.parse_args(argv)
    content = render()
    if args.check:
        current = FIXTURE.read_text(encoding="utf-8") if FIXTURE.is_file() else ""
        if current != content:
            print(
                f"{FIXTURE.relative_to(ROOT)} is out of date; "
                "run uv run python scripts/export_rust_fixtures.py",
                file=sys.stderr,
            )
            return 1
        return 0
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {FIXTURE.relative_to(ROOT)} ({len(content.encode()):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
