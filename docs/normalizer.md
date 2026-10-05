# Using the Pheasa normalizer

`pheasa.normalize` makes Khmer text that looks the same also compare the same. It puts
every syllable into the order defined by Unicode Technical Note #61 and replaces
"do not use" sequences with their preferred equivalents. It does not correct spelling.
The exact rules are in [`spec/normalization.md`](../spec/normalization.md).

## Quick start

```python
from pheasa import normalize

normalize(text)  # normalized text
normalize(text, report=True)  # text + every change + remaining issues
```

```bash
pheasa normalize input.txt -o output.txt
pheasa normalize input.txt -o output.txt --report changes.jsonl
pheasa validate input.txt                # list issues; exit status 1 if any
cat input.txt | pheasa normalize > output.txt
```

## What it changes

With default options:

| Stage | What happens | Example (code points) |
|---|---|---|
| Pre-clean | A byte order mark at the start is removed; NFC is applied | `FEFF 1780` → `1780` |
| Reorder | The marks of each syllable are put in a fixed order | `1781 17C2 17D2 1798` → `1781 17D2 1798 17C2` |
| Fold | Sequences that render the same are stored one way: coeng da as coeng ta, coeng ro second, split vowels as one, -u as a consonant shifter where one was meant | `1780 17D2 178A` → `1780 17D2 178F` |

Everything else, including spaces, ZWSP, digits and punctuation, is left alone.

If a syllable is malformed in a way that makes reordering unsafe (for example a coeng
with nothing after it), it is left exactly as typed and reported instead.

## Options

All options are off by default, because each one removes or rewrites information.

| Option | Values | Effect |
|---|---|---|
| `zwsp` | `"keep"`, `"strip"`, `"space"` | What to do with U+200B ZERO WIDTH SPACE, which marks word boundaries in Khmer |
| `digits` | `"keep"`, `"khmer"`, `"ascii"` | Convert between Khmer digits U+17E0–17E9 and 0–9. Divination numerals (U+17F0–17F9) are never converted |
| `fold_deprecated` | `False`, `True` | Replace deprecated characters (U+17A3, U+17A4, U+17D8) and remove U+17B4 and U+17B5 |
| `preserve_coeng_da` | `False`, `True` | Keep coeng da (U+17D2 U+178A) instead of storing it as coeng ta |

On the command line: `--zwsp`, `--digits`, `--fold-deprecated`, `--preserve-coeng-da`.

## Guarantees

- **Deterministic and pure.** The same input and options always give the same output,
  on every supported Python version, for Khmer text.
- **Idempotent.** `normalize(normalize(x)) == normalize(x)`.
- **NFC-stable.** The output is already NFC, so later NFC does not change it.
- **No lost consonants.** Syllables are never merged, split or reordered, and base
  consonants are never removed. Folds replace marks with visually identical
  equivalents (and coeng da with coeng ta); only the options remove characters.
- **Versioned.** `pheasa.NORMALIZATION_VERSION` (currently `"1"`) names the rule set.
  Any change to output for any input gets a new version, so hashes of normalized text
  stay comparable within a version. Store the version next to anything you hash.

## The report

`normalize(text, report=True)` returns a `Report` with three fields:

- `text`: the normalized text, identical to `normalize(text)`.
- `changes`: one `Change` per edited span, in input order, with `start` and `end`
  (offsets into the input), `before`, `after`, `output_start` (offset into the output)
  and `rules`, the rule IDs from the spec that made the change. Splicing every `after`
  into the input gives the output.
- `issues`: problems left in the output, each an `Issue` with `code`, `start`, `end` and
  `message`.

`pheasa normalize --report FILE` writes the same information as JSON lines, one change
or issue per line, with the file name and line number.

## Issue codes

`pheasa.validate(text)` checks text against the Modern Khmer syllable structure of
UTN #61 and never changes it. `normalize(report=True)` includes the same issues.

| Code | Meaning |
|---|---|
| V1 | A coeng (U+17D2) not followed by a consonant |
| V2 | A ZWNJ where it has no effect |
| V3 | A ZWJ next to Khmer text; before a coeng it marks a Middle Khmer final coeng |
| V4 | A mark that does not fit the syllable, such as a second vowel or a third coeng |
| V5 | A mark with no consonant before it |
| V6 | An old-style lunar-date sequence (digit + coeng + khan), left unconverted |
| V7 | U+17D3, a discouraged character |
| V8 | A byte order mark in the middle of the text |
| V9 | A syllable left as typed because reordering it was unsafe |

## Compatibility with other tools

Pheasa follows UTN #61 and is tested against SIL's reference script `khnormal`. The two
agree except in the cases listed in the spec under "Differences from the oracle": mostly
malformed input, where Pheasa leaves the text alone and SIL's script does not.

## Rust

The crate `pheasa` in [`rust/`](../rust/README.md) is a port of `normalize` for places
without Python, such as keyboards on phones. For every input and every combination of
options it returns the same text as the Python package, and it carries the same
`NORMALIZATION_VERSION`. The Python implementation is the reference: the crate's tests
compare it with outputs generated from Python (D-015).

```rust
use pheasa::{Options, Zwsp, normalize, normalize_with};

assert_eq!(normalize("ខែ្មរ"), "ខ្មែរ");
let options = Options { zwsp: Zwsp::Strip, ..Options::default() };
assert_eq!(normalize_with("ក\u{200B}ខ", options), "កខ");
```

`Options` has one field per Python option: `zwsp` (`Zwsp::Keep`, `Strip`, `Space`),
`digits` (`Digits::Keep`, `Khmer`, `Ascii`), `fold_deprecated` and `preserve_coeng_da`.
The report and `validate` are not ported yet.

NFC of non-Khmer characters uses the `unicode-normalization` crate (Unicode 17.0.0), not
Python's `unicodedata`. The two agree on every character assigned in both Unicode
versions. A character assigned after the older of the two can normalize differently, as
it can between Python versions. Khmer text is unaffected.

Until the crate is published, depend on it through git, pinned to a commit:

```toml
[dependencies]
pheasa = { git = "https://github.com/pheasaKhmer/pheasa", rev = "<commit>" }
```

To run its tests: `cd rust && cargo test`. The parity cases in
`rust/tests/fixtures/parity.tsv` are written by
`uv run python scripts/export_rust_fixtures.py`, and `make check` fails if they are out
of date.

## Limits

- Modern Khmer only. Middle Khmer final coengs (ZWJ + coeng) are kept at the end of the
  syllable and flagged (V3), not checked further.
- Spelling is never corrected. Two spellings that look different stay different.
