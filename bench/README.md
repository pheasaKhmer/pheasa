# Benchmark (pilot)

The Khmer benchmark's tasks, items and harness configuration. The harness itself is
`pheasa.bench` (decision D-014); run it with `pheasa bench`.

## Layout

| Path | What it holds |
|---|---|
| `tasks/<name>.toml` | A task: prompt template, scorer, output token limit, version |
| `tasks/<name>.md` | The task's one-page spec: purpose, item format, scoring, risks |
| `tasks/versions.lock.json` | Prompt hash per task version (`scripts/lock_tasks.py`) |
| `items/<name>/` | Verified items, one JSON object per line |
| `drafts/` | Unverified draft items; never scored as results |
| `cache/` | Raw model responses (not committed) |

All eight tasks are drafts (version 0.x) until a native speaker approves them.

## Running

```bash
pheasa bench bench/tasks/NAME.toml bench/items/NAME/dev.jsonl --model MODEL --dry-run
pheasa bench bench/tasks/NAME.toml bench/items/NAME/dev.jsonl --model MODEL --max-usd 5 --out results.jsonl
```

- `--dry-run` prints the item count, how many are already cached, and upper bounds on
  input tokens, output tokens and USD. It spends nothing.
- `--max-usd` is required for paid models. Before every uncached call, the harness checks
  that the call's worst case (its prompt's token bound plus the full output limit) fits
  in the remaining budget, and stops otherwise.
- Responses are cached permanently, keyed by model, task, task version, prompt hash and
  generation parameters, so a rerun never pays twice.
- Only the offline `fake:echo` and `fake:constant:TEXT` models exist until an API budget
  is approved.

### In Inspect

The same tasks run in [Inspect](https://inspect.aisi.org.uk/) with Pheasa's prompts,
items and scorers (install `inspect-ai` first):

```bash
inspect eval src/pheasa/bench/inspect_task.py@pheasa \
  -T task=bench/tasks/NAME.toml -T items=bench/items/NAME/pilot.jsonl -T lang=en --model MODEL
```

Inspect's own cache and limits apply there; the `--dry-run` estimate and the run-wide
budget are `pheasa bench` features.

## Scoring

Every scorer compares text after `pheasa.normalize`, so encoding variants never count
as errors. Scores are means with 95% bootstrap confidence intervals. With about 100 items
per task, many differences between models will not be significant, and results say so.

| Scorer | Used for |
|---|---|
| `exact` | Equal after normalization, ZWSP removal, whitespace collapsing, casefolding |
| `choice` | Multiple choice: the letter after "Answer:", else the first standalone capital |
| `chrf` | chrF++ (character 6-grams, word bigrams, beta 2), tested equal to sacreBLEU |
| `boundary_f1` | Word-boundary F1 for segmentation; 0 if other characters changed |

## Rules

- An item enters a test split only with `verified_by` and `verified_at`
  (`scripts/validate_items.py`). Draft items go to `drafts/` and only a person promotes
  them.
- Test files carry the canary string from `CANARY` once it exists.
- Changing a task's prompt requires a new version (checked by `make check`) and a
  CHANGELOG entry.
