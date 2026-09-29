# Decisions

A log of project decisions. Each entry records the context, the choice made, and the
alternatives considered.

## D-001 · 2026-09-30 · Licensing

**Context:** Pheasa ships code, datasets, and a benchmark, each with different reuse
needs.

**Choice:** Code is licensed under Apache-2.0. Data is released under CC BY 4.0, or
under stricter terms when a source requires them. The benchmark test split ships with a
canary string, and part of it is held back to limit training contamination.

**Alternatives:** MIT for code, rejected because Apache-2.0 includes a patent grant.
CC0 for data, rejected because attribution is part of the project's goals.

## D-002 · 2026-09-30 · Tooling

**Context:** The project needs reproducible environments and one check command that
behaves the same locally and in CI.

**Choice:** `uv` with a hatchling build backend, `ruff`, and `pytest` with `hypothesis`.
A `Makefile` provides `make check` (lint, tests, repository validators), and CI runs the
same target.

**Alternatives:** `just`, rejected because it adds an install step for contributors,
while `make` is already present on macOS and Linux. Poetry, rejected because `uv` is
faster and its lockfile covers the same needs.

## D-003 · 2026-09-30 · Releases through PyPI trusted publishing

**Context:** Publishing credentials should not live in the repository or on developer
machines.

**Choice:** Releases are triggered by pushing a `v*` tag. The `release.yml` workflow
checks that the tag matches `pheasa.__version__`, then publishes through PyPI trusted
publishing (OIDC) from the `pypi` environment. No API token is stored.

**Alternatives:** Manual `twine upload` with an API token, rejected because it requires
storing a long-lived secret.

## D-004 · 2026-09-30 · Hugging Face organization name

**Context:** The organization name `pheasa` was unavailable on Hugging Face.

**Choice:** Datasets, models, and the leaderboard Space are published under
`pheasaKhmer`, matching the GitHub organization. The PyPI package stays `pheasa`.

**Alternatives:** A personal namespace, rejected because project assets should live
under the project name.

## D-005 · 2026-09-30 · Normalizer follows UTN #61

**Context:** A Khmer encoding structure is already described in Unicode Technical Note
#61 and implemented by SIL International (`khnormal`, `sillsdev/khmer-normalizer`). If
Pheasa defined a second canonical form, Khmer text would have two competing standards.

**Choice:** `pheasa.normalize` implements the UTN #61 ordering exactly and is tested
against SIL's implementation. Any difference in output is treated as a bug unless the
specification explains it. Pheasa adds features around that ordering: an
invisible-character policy with ZWSP preserved by default, optional digit conversion, a
report of every change made, a streaming CLI, throughput benchmarks, and a
`NORMALIZATION_VERSION` stability guarantee.

**Alternatives:** Contributing these features upstream and depending on SIL's package,
rejected because it ties Pheasa's release cycle to another project (contributions
upstream are still welcome). A Pheasa-specific canonical form, rejected because it
would fragment Khmer text further.

## D-006 · 2026-09-30 · Pin Unicode 18.0.0

**Context:** Khmer character categories and properties must come from a fixed Unicode
version. Python's `unicodedata` version depends on the interpreter: the macOS system
Python ships Unicode 13.0.

**Choice:** Pheasa targets Unicode 18.0.0. Khmer character tables are written out
explicitly in the source, with citations, and are not read from `unicodedata` at
runtime. The Khmer entries in `UnicodeData.txt` (U+1780–17FF, U+19E0–19FF) are identical
in 15.1.0, 17.0.0, and 18.0.0, so the pin is low-risk.

**Alternatives:** Relying on the running interpreter's `unicodedata`, rejected because
it would make output depend on the Python version.

## D-007 · 2026-09-30 · SIL `khnormal` as a test oracle

**Context:** D-005 requires Pheasa to match the UTN #61 reference implementation. That
implementation (`khnormal`) is MIT-licensed, but the repository it lives in
(`sillsdev/khmer-character-specification`) is otherwise CC BY-NC-SA 4.0.

**Choice:** Vendor an unmodified copy of `khnormal` into `tests/oracle/`, with its MIT
license, the upstream commit, and a SHA-256 hash checked by a test. It is used only in
tests and is not shipped in the package. Pheasa's own implementation is written from the
UTN #61 grammar and does not copy the oracle's code. No NonCommercial-licensed material
(specification text, word lists) is included in this repository.

**Alternatives:** Downloading the oracle at test time, rejected because it makes tests
depend on the network and on upstream staying unchanged. Using the JavaScript
`khmer-normalizer`, rejected because it would add a Node toolchain to the test suite.
