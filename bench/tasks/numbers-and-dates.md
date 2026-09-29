# Task: numbers-and-dates (draft, version 0.1)

Convert numbers and dates between Khmer words, Khmer digits and Arabic digits.

**Why:** Khmer digits, spelled-out numbers and date formats appear in forms, news and official documents, and are easy to score exactly.

## Item format

One JSON object per line in `bench/items/numbers-and-dates/`:

```json
{"id": "numbers-and-dates-0001", "input": {"instruction": "...", "text": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `instruction`: what to convert, e.g. to Khmer digits or to words
- `text`: a number or date

## Model output and scoring

The prompt is in [`numbers-and-dates.toml`](./numbers-and-dates.toml). The model should reply with the converted form.

Scoring: `exact` on canonical text. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- Several spellings of numbers may be accepted; list all accepted answers or avoid ambiguous items.
- Lunar calendar dates need their own guideline (D-009 found the legacy encoding absent from web text).
