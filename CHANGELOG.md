# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `pheasa.bench`, the benchmark harness core (D-014): versioned task specs, a
  `--dry-run` cost estimate, a run-wide `--max-usd` budget, a permanent response cache,
  deterministic scorers (exact match on normalized text, multiple choice, chrF++ tested
  equal to sacreBLEU, word-boundary F1) and bootstrap confidence intervals. Run it with
  `pheasa bench`. Only offline test models exist so far.
- Eight draft pilot task specs in `bench/tasks/` (version 0.2), with a lock that
  requires a version bump whenever a prompt changes. Each task can carry prompts in
  several languages; `pheasa bench --lang km` selects the Khmer prompt once it exists.
- An item's `reference` may list several accepted answers; the best match counts.
  numbers-and-dates and register-vocabulary (now version 0.3) carry their instruction or
  context in English and Khmer.
- `scripts/draft_encoding_pairs.py`, which drafts encoding-equivalence items from
  strings attested in a corpus.
- `scripts/review_items.py`, a local page for picking draft items and prompts.

## [0.1.0] - 2026-09-30

First release. Fixes `NORMALIZATION_VERSION = "1"` (D-013).

### Added

- Project scaffolding: packaging, CI, release workflow, and repository validators.
- Normalization specification draft (`spec/normalization.md`) based on Unicode Technical Note #61.
- SIL `khnormal` vendored as a test-only oracle with pinned behavior tests.
- `pheasa.normalize` with Stage 1 (leading BOM removal, NFC) and Stage 2 (syllable
  cluster reordering per Unicode Technical Note #61).
- Property tests: differential against the oracle's sort, idempotence, NFC invariance,
  no lost base characters, and typing-order independence.
- Stage 3 folds (rules 3.1–3.9) with a `preserve_coeng_da` option. Rule 3.6 follows the
  text of Unicode Technical Note #61 where the SIL reference differs: a cluster with BA
  is weak (D-012). The differences are listed in the specification (O4–O8, conflict C4).
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
- `scripts/check_shifter_rendering.py`, a HarfBuzz check of whether text typed with the
  consonant shifter before the subscript renders like the reordered text (conflict C1).
- Golden fixture pipeline: format and workflow in `tests/golden/README.md`, a validator
  (`scripts/validate_golden.py`, run by `make check`) requiring provenance, a verifier and
  no handles or email addresses, a test that runs every fixture, and a draft tool
  (`scripts/golden_draft.py`) for preparing candidates.
- Khmer Wikipedia sample tooling: a fetch script with a provenance manifest
  (`data/wikipedia-km/manifest.jsonl`, 146 articles, CC BY-SA 4.0), a script that drafts
  fixtures from it, and an HTML review page generator.
- 70 golden fixtures from Khmer Wikipedia, verified by a native speaker.
- `scripts/encoding_variants.py`, which counts syllables that occur in more than one
  encoding in a sample.
- User guide for the normalizer (`docs/normalizer.md`).
- `scripts/lunar_probe.py`, which counts and samples legacy lunar-date sequences in a
  corpus (D-009), and `scripts/tokenizer_stats.py`, which measures how many tokens public
  tokenizers spend on Khmer compared with English, before and after normalization.
- Landscape of Khmer language technology (`reports/landscape.md`, draft): 98 datasets,
  tools, models and benchmarks with licenses checked at the source, and a gap analysis.
  Tables are rendered from `reports/landscape.jsonl` by `scripts/render_landscape.py`.
- Tokenizer cost report (`reports/tokenizers.md`, draft): on NTREX-128, Khmer costs 3.2
  to 8.5 times as many tokens as English in LLM tokenizers and 1.3 to 1.7 times in
  multilingual encoder and translation tokenizers; normalization never increased counts.
- Corpus probe report (`reports/corpus-probes.md`, draft): 61% of FineWeb-2 Khmer web
  documents contain text that `normalize` changes; no legacy lunar-date sequences in
  about 169 million characters (D-009 update).
- `scripts/fetch_sources.py`, which downloads the approved sources with provenance
  manifests under `data/`.
