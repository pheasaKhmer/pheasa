# Task: encoding-equivalence (draft, version 0.1)

Decide whether two Khmer strings spell the same word, possibly typed in a different character order.

**Why:** Khmer text is stored in many character orders that look identical (see reports/corpus-probes.md). A model that reads Khmer well should treat them as the same word and tell them apart from real spelling differences.

## Item format

One JSON object per line in `bench/items/encoding-equivalence/`:

```json
{"id": "encoding-equivalence-0001", "input": {"first": "...", "second": "..."}, "reference": "...", "verified_by": "...", "verified_at": "YYYY-MM-DD"}
```

Input fields:

- `first`: a Khmer string
- `second`: a Khmer string

## Model output and scoring

The prompt is in [`encoding-equivalence.toml`](./encoding-equivalence.toml). The model should reply with "A" (same word) or "B" (different words).

Scoring: `choice`: the letter after "Answer:", else the first standalone capital letter. Results are reported as a mean with a 95% bootstrap confidence
interval.

## Example

To be written or verified by a native speaker. Draft items go to `bench/drafts/`.

## Risks and item-writing notes

- Half the pairs should be encoding variants (built with pheasa's rules, so `normalize` maps them to the same text) and half real different words, including near-homographs.
- Variants are generated mechanically, so their correctness is checkable; the "different" pairs need a native speaker.
