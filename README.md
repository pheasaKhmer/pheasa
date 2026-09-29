# Pheasa (ភាសា)

**Open reference infrastructure for Khmer language AI.** *Pheasa* is the romanization
of ភាសា, the Khmer word for "language".

[![CI](https://github.com/pheasaKhmer/pheasa/actions/workflows/ci.yml/badge.svg)](https://github.com/pheasaKhmer/pheasa/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/pheasaKhmer/pheasa/blob/main/LICENSE)

Pheasa aims to provide:

- **a normalizer**, so that Khmer text that looks identical is also byte-identical;
- **a benchmark** for measuring how well language models handle Khmer;
- **datasets and baselines** with documented provenance.

> **Status:** pre-alpha. Nothing is published yet.

## The problem

Unicode allows several code point orders for the same visible Khmer syllable. Fonts
render them alike, but search, deduplication, tokenizers, and evaluation metrics treat
them as different strings:

| Rendered | Code points | Bytes (UTF-8) |
|---|---|---|
| ខ្មែរ | U+1781 U+17D2 U+1798 U+17C2 U+179A | `e1 9e 81 e1 9f 92 e1 9e 98 e1 9f 82 e1 9e 9a` |
| ខែ្មរ | U+1781 U+17C2 U+17D2 U+1798 U+179A | `e1 9e 81 e1 9f 82 e1 9f 92 e1 9e 98 e1 9e 9a` |

Unicode NFC does not reconcile these. Pheasa's normalizer does, following the Khmer
encoding structure described in
[Unicode Technical Note #61](https://www.unicode.org/notes/tn61/).

```python
from pheasa import normalize

assert normalize("ខែ្មរ") == normalize("ខ្មែរ") == "ខ្មែរ"
```

`normalize(text, report=True)` also returns every change it made, with input offsets
and the rule responsible, plus any problems it could not safely fix. Options that remove
or rewrite information (`zwsp`, `digits`, `fold_deprecated`) are off by default.

From the command line:

```bash
pheasa normalize input.txt -o output.txt --report changes.jsonl
pheasa validate input.txt
```

See the [user guide](https://github.com/pheasaKhmer/pheasa/blob/main/docs/normalizer.md) for options, the report format and issue
codes. The rules are specified in [`spec/normalization.md`](https://github.com/pheasaKhmer/pheasa/blob/main/spec/normalization.md).

## Install

```bash
pip install pheasa   # available once v0.1 is released
```

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
make check
```

## Acknowledgements

Pheasa builds on the Khmer encoding structure work by SIL International
([`khmer-character-specification`](https://github.com/sillsdev/khmer-character-specification))
and Unicode Technical Note #61.

## Citation

If you use Pheasa, please cite it using [`CITATION.cff`](https://github.com/pheasaKhmer/pheasa/blob/main/CITATION.cff).

## License

Code is licensed under [Apache-2.0](https://github.com/pheasaKhmer/pheasa/blob/main/LICENSE). Datasets are released under CC BY 4.0
unless their sources require stricter terms.

---

Created and maintained by **Samputhy Khim** ([@organi-cs](https://github.com/organi-cs), [ORCID 0009-0008-4510-8839](https://orcid.org/0009-0008-4510-8839)).
