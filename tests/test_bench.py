"""Tests for the benchmark harness core (pheasa.bench, D-014)."""

import json
import math

import pytest
import sacrebleu
from hypothesis import given, settings
from hypothesis import strategies as st
from test_normalize import cps

from pheasa.bench import metrics, runner, stats
from pheasa.bench.cache import ResponseCache, cache_key
from pheasa.bench.providers import FakeProvider
from pheasa.cli import main

TEXT = st.text(
    alphabet=st.sampled_from([*"abcde .,!?'()", "ក", "ខ", "ា", "្", "​"]),
    max_size=40,
)


@settings(max_examples=500)
@given(TEXT, TEXT)
def test_chrf_matches_sacrebleu(hypothesis, reference):
    hyp, ref = metrics.canonical(hypothesis), metrics.canonical(reference)
    expected = sacrebleu.sentence_chrf(hyp, [ref], word_order=2).score
    assert math.isclose(metrics.chrf(hypothesis, reference), expected, abs_tol=1e-9)


@settings(max_examples=200)
@given(st.lists(st.tuples(TEXT, TEXT), min_size=1, max_size=5))
def test_corpus_chrf_matches_sacrebleu(pairs):
    hyps = [metrics.canonical(h) for h, _ in pairs]
    refs = [metrics.canonical(r) for _, r in pairs]
    expected = sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score
    assert math.isclose(metrics.corpus_chrf(pairs), expected, abs_tol=1e-9)


def test_exact_ignores_encoding_variants():
    misordered = cps(0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A)
    canonical = cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A)
    assert metrics.exact(misordered + "​", " " + canonical) == 1.0
    assert metrics.exact("Hello  World", "hello world") == 1.0
    assert metrics.exact("a", "b") == 0.0


@pytest.mark.parametrize(
    ("prediction", "expected"),
    [("Answer: B", 1.0), ("answer:(b)", 1.0), ("B", 1.0), ("I pick C", 0.0), ("none", 0.0)],
)
def test_choice(prediction, expected):
    assert metrics.choice(prediction, "B") == expected


@pytest.mark.parametrize(
    ("prediction", "reference", "expected"),
    [
        ("ab​cd ef", "ab cd ef", 1.0),
        ("abcd ef", "ab cd ef", 2 / 3),
        ("abcdef", "abcdef", 1.0),
        ("ab cdx", "ab cd", 0.0),  # the text itself changed
        ("a b c", "abc", 0.0),
    ],
)
def test_boundary_f1(prediction, reference, expected):
    assert math.isclose(metrics.boundary_f1(prediction, reference), expected)


def test_bootstrap_is_deterministic_and_brackets_the_mean():
    scores = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1] * 5
    mean, low, high = stats.bootstrap_ci(scores)
    assert low <= mean <= high and (mean, low, high) == stats.bootstrap_ci(scores)
    diff, d_low, d_high = stats.paired_difference_ci(scores, scores)
    assert diff == d_low == d_high == 0
    with pytest.raises(ValueError):
        stats.paired_difference_ci([1], [1, 0])


def test_cache_key_covers_version_and_params():
    base = cache_key("m", "t", "1", "prompt", {"temperature": 0})
    assert base != cache_key("m", "t", "2", "prompt", {"temperature": 0})
    assert base != cache_key("m", "t", "1", "prompt!", {"temperature": 0})
    assert base != cache_key("m", "t", "1", "prompt", {"temperature": 1})
    assert base == cache_key("m", "t", "1", "prompt", {"temperature": 0})


TASK = """
name = "echo-test"
version = "1"
description = "Repeat the last line."
scorer = "exact"
max_tokens = 16
[prompts]
en = \"\"\"Repeat the word.
{word}\"\"\"
"""


@pytest.fixture
def task_files(tmp_path):
    (tmp_path / "task.toml").write_text(TASK, encoding="utf-8")
    items = [{"id": f"i{n}", "input": {"word": w}, "reference": w} for n, w in enumerate("abc")]
    items[2]["reference"] = "z"  # one wrong answer
    lines = [json.dumps({"canary": "x"}), *(json.dumps(i) for i in items)]
    (tmp_path / "items.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def test_run_caches_and_scores(task_files):
    task = runner.load_task(task_files / "task.toml")
    items = runner.load_items(task_files / "items.jsonl")
    provider, cache = FakeProvider("fake:echo"), ResponseCache(task_files / "cache")
    guess = runner.estimate(task, items, provider, cache)
    assert (guess.items, guess.cached, guess.output_tokens) == (3, 0, 48)
    results, spent = runner.run(task, items, provider, cache, max_usd=1.0)
    assert [r["score"] for r in results] == [1.0, 1.0, 0.0] and spent > 0
    again, spent_again = runner.run(task, items, provider, cache, max_usd=0.0)
    assert spent_again == 0 and all(r["cached"] for r in again)
    assert runner.estimate(task, items, provider, cache).usd == 0


def test_run_stops_before_the_budget_is_exceeded(task_files):
    task = runner.load_task(task_files / "task.toml")
    items = runner.load_items(task_files / "items.jsonl")
    provider = FakeProvider("fake:echo")
    worst = provider.cost(provider.max_tokens_for(task.render(items[0])), task.max_tokens)
    budget = worst * 1.5
    with pytest.raises(runner.BudgetExceeded) as stop:
        runner.run(task, items, provider, ResponseCache(task_files / "c"), max_usd=budget)
    done, spent = len(stop.value.results), stop.value.spent
    next_worst = provider.cost(provider.max_tokens_for(task.render(items[done])), task.max_tokens)
    # Stopped early, within budget, and only because the next worst case would not fit.
    assert done < len(items) and spent <= budget < spent + next_worst


def test_bench_command(task_files, capsys):
    base = [str(task_files / "task.toml"), str(task_files / "items.jsonl"), "--model", "fake:echo"]
    base += ["--cache", str(task_files / "cache")]
    assert main(["bench", *base, "--dry-run"]) == 0
    assert "3 items (0 cached)" in capsys.readouterr().out
    assert main(["bench", *base, "--out", str(task_files / "out.jsonl")]) == 0
    assert "score 0.667" in capsys.readouterr().out
    assert len((task_files / "out.jsonl").read_text().splitlines()) == 3


def test_prompt_language(task_files, capsys):
    task = runner.load_task(task_files / "task.toml")
    with pytest.raises(ValueError, match="no 'km' prompt"):
        task.render({"input": {"word": "a"}}, "km")
    base = [str(task_files / "task.toml"), str(task_files / "items.jsonl"), "--model", "fake:echo"]
    assert main(["bench", *base, "--lang", "km", "--dry-run"]) == 2
    assert "no 'km' prompt" in capsys.readouterr().err


def test_several_accepted_references(tmp_path):
    (tmp_path / "task.toml").write_text(TASK, encoding="utf-8")
    item = {"id": "x", "input": {"word": "b"}, "reference": ["a", "b"]}
    task = runner.load_task(tmp_path / "task.toml")
    results, _ = runner.run(
        task, [item], FakeProvider("fake:echo"), ResponseCache(tmp_path / "c"), 1
    )
    assert results[0]["score"] == 1.0
