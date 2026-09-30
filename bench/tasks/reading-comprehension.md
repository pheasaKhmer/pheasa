# Task: reading-comprehension (draft, version 0.2)

Answer a multiple-choice question about a short Khmer passage.

**Why:** Belebele covers Khmer only through translation from English; native Khmer passages test knowledge of Khmer contexts.

## Item format

One JSON object per line in `bench/items/reading-comprehension/`:

```json
{"id": "reading-comprehension-0001", "input": {"passage": "...", "question": "...", "a": "...", "b": "...", "c": "...", "d": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `passage`: a Khmer passage
- `question`: a Khmer question
- `a`: option A
- `b`: option B
- `c`: option C
- `d`: option D

## Model output and scoring

The prompts (English, and Khmer once verified) are in [`reading-comprehension.toml`](./reading-comprehension.toml). The model should reply with the letter of the correct option, "A" to "D".

Scoring: `choice`. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- The correct letter should be balanced across A to D.
- Questions must need the passage: check that they cannot be answered without it.
