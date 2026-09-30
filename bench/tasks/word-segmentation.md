# Task: word-segmentation (draft, version 0.2)

Insert a space between the words of a Khmer sentence written without word breaks.

**Why:** Word segmentation underlies search, spell-checking and many NLP pipelines, and the landscape report found several segmenters but no shared test set.

## Item format

One JSON object per line in `bench/items/word-segmentation/`:

```json
{"id": "word-segmentation-0001", "input": {"sentence": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `sentence`: a Khmer sentence without spaces or ZWSP

## Model output and scoring

The prompts (English, and Khmer once verified) are in [`word-segmentation.toml`](./word-segmentation.toml). The model should reply with the same sentence with one space (or ZWSP) between words.

Scoring: `boundary_f1`: F1 over word-boundary positions; 0 if the model changed any character of the sentence. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- Segmentation conventions differ (compounds, particles); the guideline used by the annotator must be written down with the items.
- Items must not come from segmenter training corpora.
