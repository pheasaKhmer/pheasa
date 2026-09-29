# Task: translation-en-km (draft, version 0.1)

Translate an English sentence into Khmer.

**Why:** Writing Khmer is harder for models than reading it, and matters for every Khmer-facing product.

## Item format

One JSON object per line in `bench/items/translation-en-km/`:

```json
{"id": "translation-en-km-0001", "input": {"source": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `source`: an English sentence

## Model output and scoring

The prompt is in [`translation-en-km.toml`](./translation-en-km.toml). The model should reply with a Khmer reference translation.

Scoring: `chrf` on canonical Khmer: both sides are normalized first, so encoding variants are not penalized. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- As above for contamination and single references.
- chrF++ word bigrams use spaces, which Khmer mostly lacks, so the score is dominated by character n-grams.
