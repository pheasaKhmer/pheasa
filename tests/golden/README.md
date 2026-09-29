# Golden fixtures

Real Khmer text and the normalized output that a native speaker has checked. They pin
Pheasa's behavior: any change to these outputs needs a new `NORMALIZATION_VERSION`, a
`CHANGELOG.md` entry and a `DECISIONS.md` entry.

`normalization.jsonl` holds one JSON object per line:

| Field | Meaning |
|---|---|
| `id` | `G-0001`, `G-0002`, … unique across all files |
| `input` | the text as found, after removing personal data |
| `expected` | the verified output of `normalize(input, **options)` |
| `options` | optional; `normalize` keyword options, e.g. `{"zwsp": "strip"}` |
| `source` | where the text came from (URL or citation) |
| `license` | the source's license; skip sources that forbid reuse |
| `retrieved` | ISO date the text was retrieved |
| `transform` | what was done to it, e.g. `"one sentence; handle removed"` |
| `verified_by` | the verifier's name or annotator ID |
| `verified_at` | ISO date of verification |

Extra fields (such as the code points added by the draft tool) are allowed.

## Adding fixtures

1. Put candidate lines in a text file and run
   `uv run python scripts/golden_draft.py lines.txt --source … --license … --retrieved …
   --transform … --out tests/golden/drafts/NAME.jsonl`.
   Lines containing an @handle or an email address are skipped.
2. For each draft, check that `expected` is the correct form of `input`. The draft lists
   the rules that fired and the code points of both sides.
3. Fill in `verified_by` and `verified_at`, and move the line to `normalization.jsonl`.
   If `expected` is wrong, do not edit it: record the case in an issue instead, since
   it means the normalizer needs a change.

`make check` validates every record (`scripts/validate_golden.py`) and runs it through
the normalizer (`tests/test_golden.py`). Files in `drafts/` are not checked.
