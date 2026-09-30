# Task: register-vocabulary (draft, version 0.3)

Choose the word of the right register (royal, monastic or common) for a context.

**Why:** Khmer uses different words for the same action depending on whether the subject is royal, monastic or ordinary. This is cultural knowledge that translated benchmarks miss.

## Item format

One JSON object per line in `bench/items/register-vocabulary/`:

```json
{"id": "register-vocabulary-0001", "input": {"context_en": "...", "context_km": "...", "a": "...", "b": "...", "c": "...", "d": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `context_en`, `context_km`: who is speaking about whom (e.g. addressing a monk), in
  English and in Khmer
- `a`: option A
- `b`: option B
- `c`: option C
- `d`: option D

## Model output and scoring

The prompts (English, and Khmer once verified) are in [`register-vocabulary.toml`](./register-vocabulary.toml). The model should reply with the letter of the correct option, "A" to "D".

Scoring: `choice`. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- Distractors should be real words of the other registers, not nonsense.
- Regional and generational usage may differ; items need a clear, documented standard.
