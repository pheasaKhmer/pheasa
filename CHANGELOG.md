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
