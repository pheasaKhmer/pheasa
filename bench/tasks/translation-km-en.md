# Task: translation-km-en (draft, version 0.1)

Translate a Khmer sentence into English.

**Why:** Understanding Khmer is most directly measured by translating it.

## Item format

One JSON object per line in `bench/items/translation-km-en/`:

```json
{"id": "translation-km-en-0001", "input": {"source": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `source`: a Khmer sentence

## Model output and scoring

The prompt is in [`translation-km-en.toml`](./translation-km-en.toml). The model should reply with an English reference translation.

Scoring: `chrf`: chrF++ (character 6-grams and word bigrams, beta 2), identical to sacreBLEU on canonical text. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- Must not reuse public test sets (FLORES, NTREX), which models may have seen in training.
- A single reference underrates valid alternative translations; report chrF++ only as a comparison between systems.
