"""Run a benchmark task: estimate cost, enforce the budget, cache and score responses."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pheasa.bench.cache import ResponseCache, cache_key
from pheasa.bench.metrics import boundary_f1, choice, chrf, exact
from pheasa.bench.providers import Provider
from pheasa.bench.stats import bootstrap_ci

__all__ = ["BudgetExceeded", "Estimate", "Task", "estimate", "load_items", "load_task", "run"]

SCORERS: dict[str, Callable[[str, str], float]] = {
    "exact": exact,
    "choice": choice,
    "chrf": chrf,
    "boundary_f1": boundary_f1,
}


@dataclass(frozen=True)
class Task:
    """A task spec: bench/tasks/<name>.toml. `prompts` maps a language code ("en", "km")
    to a prompt template; changing any prompt requires a new `version`."""

    name: str
    version: str
    description: str
    prompts: dict[str, str]
    scorer: str
    max_tokens: int

    def render(self, item: dict, lang: str = "en") -> str:
        if lang not in self.prompts:
            raise ValueError(
                f"task {self.name} has no {lang!r} prompt (has {sorted(self.prompts)})"
            )
        return self.prompts[lang].format(**item["input"])


def load_task(path: Path | str) -> Task:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    task = Task(**{field: data[field] for field in Task.__dataclass_fields__})
    if task.scorer not in SCORERS:
        raise ValueError(f"{path}: unknown scorer {task.scorer!r}")
    return task


def load_items(path: Path | str) -> list[dict]:
    """Items as dicts, skipping the canary header line of test files (validate_items.py)."""
    records = [json.loads(line) for line in Path(path).read_text("utf-8").splitlines() if line]
    return [record for record in records if set(record) != {"canary"}]


@dataclass(frozen=True)
class Estimate:
    items: int
    cached: int
    input_tokens: int
    output_tokens: int
    usd: float


def _params(task: Task, lang: str) -> dict:
    return {"max_tokens": task.max_tokens, "temperature": 0, "prompt_language": lang}


def estimate(
    task: Task, items: list[dict], provider: Provider, cache: ResponseCache, lang: str = "en"
) -> Estimate:
    """Upper bound on what running `items` would cost. Cached items cost nothing."""
    cached = input_tokens = output_tokens = 0
    for item in items:
        prompt = task.render(item, lang)
        key = cache_key(provider.name, task.name, task.version, prompt, _params(task, lang))
        if cache.get(key) is not None:
            cached += 1
            continue
        input_tokens += provider.max_tokens_for(prompt)
        output_tokens += task.max_tokens
    usd = provider.cost(input_tokens, output_tokens)
    return Estimate(len(items), cached, input_tokens, output_tokens, usd)


class BudgetExceeded(RuntimeError):
    def __init__(self, spent: float, results: list[dict]) -> None:
        super().__init__(f"stopped at ${spent:.4f}: the next call could exceed --max-usd")
        self.spent, self.results = spent, results


def run(
    task: Task,
    items: list[dict],
    provider: Provider,
    cache: ResponseCache,
    max_usd: float,
    lang: str = "en",
) -> tuple[list[dict], float]:
    """Score every item, reusing cached responses. Returns (results, USD spent).

    Before each uncached call, the worst case (the prompt's token bound plus the full
    output budget) must fit in what is left of `max_usd`; otherwise BudgetExceeded is
    raised with the results so far.
    """
    score = SCORERS[task.scorer]
    results, spent = [], 0.0
    for item in items:
        prompt = task.render(item, lang)
        key = cache_key(provider.name, task.name, task.version, prompt, _params(task, lang))
        entry, cost = cache.get(key), 0.0
        cached = entry is not None
        if not cached:
            worst = provider.cost(provider.max_tokens_for(prompt), task.max_tokens)
            if spent + worst > max_usd:
                raise BudgetExceeded(spent, results)
            response = provider.generate(prompt, task.max_tokens)
            cost = provider.cost(response.input_tokens, response.output_tokens)
            spent += cost
            entry = {
                "model": provider.name,
                "task": task.name,
                "task_version": task.version,
                "prompt": prompt,
                "params": _params(task, lang),
                "response": response.text,
                "usage": {"input": response.input_tokens, "output": response.output_tokens},
            }
            cache.put(key, entry)
        results.append(
            {
                "id": item["id"],
                "response": entry["response"],
                "score": score(entry["response"], item["reference"]),
                "cached": cached,
                "usd": cost,
            }
        )
    return results, spent


def summarize(results: list[dict]) -> dict:
    mean, low, high = bootstrap_ci([r["score"] for r in results])
    return {"items": len(results), "mean": mean, "ci95": [low, high]}
