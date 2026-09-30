"""The Inspect exporter (D-014). Skipped where inspect-ai is not installed (as in CI)."""

import json

import pytest

inspect_ai = pytest.importorskip("inspect_ai")

from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from pheasa.bench.inspect_task import pheasa  # noqa: E402

TASK = """
name = "echo-test"
version = "1"
description = "Repeat the word."
scorer = "exact"
max_tokens = 16
[prompts]
en = \"\"\"Repeat the word.
{word}\"\"\"
"""


def test_inspect_run_uses_pheasa_scoring(tmp_path):
    (tmp_path / "task.toml").write_text(TASK, encoding="utf-8")
    misordered = "ខែ្ម"
    canonical = "ខ្មែ"
    items = [
        {"id": "a", "input": {"word": "x"}, "reference": ["x", "y"]},
        {"id": "b", "input": {"word": canonical}, "reference": canonical},
        {"id": "c", "input": {"word": "z"}, "reference": "z"},
    ]
    (tmp_path / "items.jsonl").write_text("\n".join(json.dumps(i) for i in items), encoding="utf-8")
    outputs = [
        ModelOutput.from_content("mockllm/model", "y"),  # second accepted reference
        ModelOutput.from_content("mockllm/model", misordered),  # encoding variant
        ModelOutput.from_content("mockllm/model", "wrong"),
    ]
    model = get_model("mockllm/model", custom_outputs=outputs)
    task = pheasa(task=str(tmp_path / "task.toml"), items=str(tmp_path / "items.jsonl"))
    [log] = inspect_ai.eval(
        task, model=model, log_dir=str(tmp_path / "logs"), display="none", max_samples=1
    )
    assert log.status == "success"
    assert log.eval.task_version in ("1", 1)
    scores = {s.id: s.scores["pheasa_scorer"].value for s in log.samples}
    assert scores == {"a": 1.0, "b": 1.0, "c": 0.0}


def test_relative_paths_resolve_from_start_directory(tmp_path, monkeypatch):
    from pheasa.bench.inspect_task import _resolve

    (tmp_path / "bench").mkdir()
    (tmp_path / "bench" / "task.toml").write_text(TASK, encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)  # as Inspect does
    monkeypatch.setenv("PWD", str(tmp_path))
    assert _resolve("bench/task.toml") == tmp_path / "bench" / "task.toml"
