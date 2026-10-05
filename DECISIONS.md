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

## D-008 · 2026-09-30 · Fold COENG DA into COENG TA by default

**Context:** UTN #61 (pp. 31–32) says Modern Khmer should store coeng da
(`17D2 178A`) as coeng ta (`17D2 178F`), because the two render identically and are
routinely confused. Folding them loses a spelling distinction that some downstream uses
(spell-checking, text-to-speech, orthography research) may want.

**Choice:** Fold by default, matching UTN #61 and the SIL reference implementation.
Native-speaker review confirmed that Khmer readers cannot tell the two apart without
inspecting code points. `preserve_coeng_da=True` turns the fold off.

**Alternatives:** Preserving coeng da by default, rejected because it leaves identical
text encoded two ways, which is the problem normalization exists to solve.

## D-009 · 2026-09-30 · Legacy lunar-date sequences are flagged, not converted

**Context:** UTN #61 (p. 35) says legacy digit + coeng + khan sequences (for example
`17E0 17D2 17D4`, often rendered like U+19E0) should be replaced with the Khmer lunar
symbols U+19E0–19FF. The SIL reference implementation contains this substitution, but it
never runs, because digits end a syllable cluster before the substitution step. Native-
speaker review reports that digit + coeng + khan also appears in real text as typing and
OCR errors unrelated to dates, so a blanket conversion could insert lunar symbols where
none were meant.

**Choice:** Normalization version 1 leaves these sequences unchanged and flags them in
the validation report. Conversion will be revisited once corpus counts (Phase 2) show how
often each reading occurs.

**Alternatives:** Converting every occurrence as UTN #61 describes, rejected because the
sequence is ambiguous in real data and the conversion is not reversible.

**Update 2026-09-30 (Phase 2 corpus counts):** no full legacy sequence occurs in about
169 million characters (FineWeb-2 `khm_Khmr` test split and the full Khmer Wikipedia
dump); 15 partial matches have the structure of typing slips. The decision stands. See
`reports/corpus-probes.md`. Removing the
stray coeng, rejected because it would silently destroy a possible lunar-date encoding.

## D-010 · 2026-09-30 · Leave unstable clusters unsorted

**Context:** D-005 makes the SIL oracle the reference for Stage 2. The spec also requires
`normalize` to be idempotent and NFC-stable, because downstream users hash its output.
Property testing showed that the oracle's sort is not idempotent when a cluster holds a
dangling COENG or a stray ZWJ: the joiner sorts to the end of the cluster and pulls the
next syllable's base in as a subscript, and a second pass sorts the merged cluster
differently. A cluster followed by a non-Khmer combining mark can likewise end up in an
order that NFC changes.

**Choice:** Spec rule 2.3. Pheasa sorts a cluster only if the sorted form keeps the
cluster boundary and NFC order with the next character. Otherwise it leaves the cluster
as typed and flags it. The spec lists these as oracle differences O1 and O2. A run of
leading U+FEFF is removed as a whole (rule 1.1) for the same idempotence reason.
`NORMALIZATION_VERSION` is `"0"` until every stage of the spec is implemented.

**Alternatives:** Matching the oracle exactly, rejected because output that changes on a
second pass breaks deduplication. Sorting repeatedly until nothing changes, rejected
because it would silently turn more of the following text into subscripts.

**Decided by:** engineering, under the conservative-default rule for malformed input.

## D-011 · 2026-09-30 · Rule 3.6 follows UTN #61's text where the oracle differs

**Context:** Rule 3.6 turns a -u typed in place of a consonant shifter into triisap or
muusikatoan, depending on whether the consonant cluster is STRONG. Checking the SIL
oracle against the UTN #61 text found three problems. The oracle's weak class has
`1780` where UTN #61 p. 23 has `1789` (NYO); the same typo is on UTN #61 p. 24. The
oracle converts -u before samyok sannya to triisap, but UTN #61 p. 25 says samyok sannya
does not push triisap down. And UTN #61's prose (BA always makes a cluster weak) and its
lookbehind regex (which can match a strong consonant after a BA) disagree, and the oracle
follows the regex. Separately, the oracle's single pass is not idempotent when a fold
leaves the cluster unsorted.

**Choice:** Pheasa treats NYO as weak, leaves -u before samyok sannya in strong clusters,
and leaves the -u unchanged (flagged) where the prose and the regex disagree. Each
cluster is sorted and folded repeatedly until it stops changing (rule 3.9). These are
oracle differences O4–O7 in the spec. Q-008 asks the human which reading of the BA case
is right.

**Alternatives:** Matching the oracle exactly, rejected because it copies a typo, changes
rendering in the samyok case, and is not idempotent. Following the prose in the BA case
without asking, rejected because the sources conflict, so the conservative default
applies until a native speaker decides.

**Decided by:** engineering, from the UTN #61 text. The BA case was later settled by D-012.

## D-012 · 2026-09-30 · STRONG follows UTN #61's prose

**Context:** Rule 3.6 needs to know whether a consonant cluster is STRONG (takes
triisap) or WEAK (takes muusikatoan). UTN #61's prose (pp. 17, 22) says a cluster with
BA is weak, and one with a series 1 consonant and no BA is strong. Its regex (p. 16) is
a lookbehind that matches any suffix of the cluster, so it calls `BA + coeng KA` strong
and can miss a strong base behind three coengs. SIL's reference follows the regex. D-011
left these cases unchanged until a native speaker decided (Q-008).

**Choice:** Follow the prose everywhere: in rule 3.6 and in the validator's check of
where ZWNJ may follow a shifter. Recorded as oracle difference O7.

**Alternatives:** Following the regex and SIL (triisap after BA + series 1 coeng),
rejected because the prose states the BA rule explicitly (p. 22, rule 3). Leaving the -u
unchanged, rejected once the native-speaker answer was available.

**Decided by:** the human (Q-008 answer A), 2026-09-30.

## D-013 · 2026-09-30 · Normalization version 1

**Context:** Downstream users hash normalized text, so the output has to be stable and
identified. All four stages and the validation step of `spec/normalization.md` are
implemented, every source conflict has a recorded resolution (C1 by Q-009, C4 by Q-008),
and 70 golden fixtures from Khmer Wikipedia have been verified by a native speaker.

**Choice:** `NORMALIZATION_VERSION = "1"` from pheasa 0.1.0. From here, any change to the
output for any input (not only the golden fixtures) needs version "2", a CHANGELOG entry
and a DECISIONS entry. Validation messages and report fields may change without a new
normalization version, because they do not change the text.

**Alternatives:** Waiting for fixtures from messier sources (social media, OCR), rejected
because version numbers exist so that later changes can be made safely; the next rule
change will simply be version "2".

**Decided by:** engineering, after the human answered Q-008 and verified the fixtures.

## D-014 · 2026-09-30 · Own harness core, adapters for existing frameworks

**Context:** The pilot probe needs a harness. Project rules require a `--dry-run` that
prints item count, estimated tokens and estimated USD; a `--max-usd` that aborts the
whole run; and a permanent cache of raw responses keyed by (model, task version, prompt
hash, parameters), so a rerun never pays twice. Adoption is more likely if people can run
the tasks in the frameworks they already use. Checked on 2026-09-30 (both MIT licensed,
actively maintained):
- Inspect (UK AISI) caches responses keyed by model, prompt, epoch and generation
  settings, but for one week by default and without a task version in the key. It has a
  USD `cost_limit`, applied per sample, and no dry-run estimate.
- lm-evaluation-harness caches responses in SQLite (`--use_cache`) and has no cost,
  budget or dry-run option.

**Choice:** A small harness core in Pheasa (`pheasa.bench`) for items, versioned
prompts, the dry-run estimate, a run-wide budget, the permanent response cache,
deterministic scoring and bootstrap confidence intervals. Model access goes through thin
provider adapters. Once the task format settles, add an exporter that turns each task
into an Inspect task, so others can run it there.

**Alternatives:** Building directly on Inspect, rejected for now because its cache
expires and does not know task versions, and its cost limit is per sample. Building on
lm-evaluation-harness, rejected because it has no cost controls and is centered on local
models. Both remain export targets.

**Decided by:** engineering.

## D-015 · 2026-10-06 · Rust port of the normalizer, held to the Python output

**Context:** A Rust keyboard core needs the normalizer on phones, where Python is not
available. Normalized text is hashed and deduplicated (D-013), so text normalized on a
phone must be byte-identical to text normalized by the Python package, for every input
and option.

**Choice:** A Rust crate, `pheasa`, in `rust/`, that ports `normalize` with all its
options (Stages 1 to 4). The Python implementation stays the reference, and
`NORMALIZATION_VERSION` names the output of both: a rule change needs a new version and
lands in both. `scripts/export_rust_fixtures.py` writes `rust/tests/fixtures/parity.tsv`
from the Python implementation: every golden fixture input, every Khmer and
test-alphabet character in a few contexts, and 22,500 strings built from the alphabets
and tokens of the property tests with fixed seeds, each with its output under every
combination of options that can change it. The Rust tests require identical output for
all 24,040 inputs under all 36 option combinations. `make check` fails if the file is
out of date, and CI runs `cargo fmt`, `cargo clippy` (pedantic) and `cargo test`. NFC of
non-Khmer text comes from the `unicode-normalization` crate, pinned to 0.1.25 (Unicode
17.0.0), while Python uses its interpreter's `unicodedata` (Unicode 14.0.0 to 16.0.0 on
the supported versions). Unicode's normalization stability policy makes their NFC the
same for every character assigned in both versions, which a comparison of every code
point against Python 3.12 and 3.14 confirmed. Characters assigned in between can
normalize differently, as they already can between Python versions (spec rule 1.3). The
report (`report=True`) and `validate` are not ported yet.

**Alternatives:** Calling Python from the keyboard, rejected because embedding an
interpreter in a phone keyboard costs size and startup time. A C library used by both
languages, rejected because it would replace the reference implementation and add a
native build to the Python package. Porting only the Stage 2 reorder, rejected because
the folds and options also change the output, so hashes would differ. Writing NFC by
hand to avoid the dependency, rejected because it needs the full Unicode decomposition
and composition tables. Pinning `unicode-normalization` exactly means a dependent cannot
pick up a newer 0.1 release while it depends on this crate; that is accepted, because a
newer release can change NFC and so the output.

**Decided by:** engineering.
