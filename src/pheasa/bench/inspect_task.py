"""Run a Pheasa benchmark task in Inspect (D-014).

    inspect eval src/pheasa/bench/inspect_task.py@pheasa \
        -T task=bench/tasks/NAME.toml -T items=bench/items/NAME/pilot.jsonl -T lang=en \
        --model MODEL

The prompts, items, accepted references and scorers are Pheasa's own, so scores match
`pheasa bench` for the same responses. Inspect's own cache, limits and logs apply;
Pheasa's `--dry-run` estimate and run-wide budget do not. Needs `inspect-ai` installed.
"""

from __future__ import annotations

import os
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState, generate

from pheasa.bench.runner import SCORERS, load_items, load_task, references

__all__ = ["pheasa", "pheasa_scorer"]


@scorer(metrics=[mean(), stderr()])
def pheasa_scorer(name: str):
    """Score with a Pheasa scorer; the best of several accepted references counts."""
    score_one = SCORERS[name]

    async def score(state: TaskState, target: Target) -> Score:
        answer = state.output.completion
        value = max(score_one(answer, reference) for reference in target.target)
        return Score(value=value, answer=answer)

    return score


def _resolve(path: str) -> Path:
    """Inspect runs a task from the task file's directory, so a relative path is looked up
    from the directory the command was started in (PWD), then from the source checkout."""
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    for base in (Path(os.environ.get("PWD", ".")), Path(__file__).resolve().parents[3]):
        if (base / candidate).exists():
            return base / candidate
    return candidate


@task
def pheasa(task: str, items: str, lang: str = "en") -> Task:
    spec = load_task(_resolve(task))
    samples = [
        Sample(input=spec.render(item, lang), target=references(item), id=item["id"])
        for item in load_items(_resolve(items))
    ]
    return Task(
        dataset=samples,
        solver=generate(),
        scorer=pheasa_scorer(spec.scorer),
        config=GenerateConfig(max_tokens=spec.max_tokens, temperature=0),
        name=f"pheasa-{spec.name}-{lang}",
        version=spec.version,
    )
