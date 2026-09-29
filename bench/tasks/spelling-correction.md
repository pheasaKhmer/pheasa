# Task: spelling-correction (draft, version 0.1)

Correct the one misspelled word in a Khmer sentence and return the whole sentence.

**Why:** Spelling knowledge is a basic test of written Khmer, and real text contains common misspellings.

## Item format

One JSON object per line in `bench/items/spelling-correction/`:

```json
{"id": "spelling-correction-0001", "input": {"sentence": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `sentence`: a Khmer sentence with one misspelled word

## Model output and scoring

The prompt is in [`spelling-correction.toml`](./spelling-correction.toml). The model should reply with the corrected sentence.

Scoring: `exact`: equal after `pheasa.normalize`, ZWSP removal and whitespace collapsing, so encoding differences are not counted as errors. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- Some misspellings have more than one accepted correction; such items should be rewritten or dropped.
- The misspelling must not be an encoding variant, which `normalize` would already fix.
