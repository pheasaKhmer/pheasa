# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project scaffolding: packaging, CI, release workflow, and repository validators.
- Normalization specification draft (`spec/normalization.md`) based on Unicode Technical Note #61.
- SIL `khnormal` vendored as a test-only oracle with pinned behavior tests.
- `pheasa.normalize` with Stage 1 (leading BOM removal, NFC) and Stage 2 (syllable
  cluster reordering per Unicode Technical Note #61). `NORMALIZATION_VERSION` is `"0"`
  while the specification is only partly implemented.
- Property tests: differential against the oracle's sort, idempotence, NFC invariance,
  no lost base characters, and typing-order independence.
- Stage 3 folds (rules 3.1–3.9) with a `preserve_coeng_da` option. Rule 3.6 follows the
  text of Unicode Technical Note #61 where the SIL reference differs; the differences
  are listed in the specification (O4–O7, conflict C4).
- Stage 4 options, all off by default: `zwsp` (`"keep"`, `"strip"`, `"space"`), `digits`
  (`"keep"`, `"khmer"`, `"ascii"`) and `fold_deprecated`.
- `pheasa.validate`, a checker for the Modern Khmer syllable structure of Unicode
  Technical Note #61 (issue codes V1–V9), and `normalize(text, report=True)`, which
  returns the normalized text, every change with input offsets and rule IDs, and the
  remaining issues.
- Command-line interface: `pheasa normalize` (streams line by line, all options,
  `--report` as JSON lines) and `pheasa validate` (exit status 1 if issues are found).
- Throughput benchmark (`scripts/bench_throughput.py`), run by `make check` and CI, which
  fails on superlinear slowdowns or throughput below a floor.

### Changed

- `normalize` reuses the result for a repeated syllable cluster within one call, roughly
  doubling throughput. Output is unchanged.
