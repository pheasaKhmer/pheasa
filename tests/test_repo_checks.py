import importlib.util
import json
import string
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_attribution = load("check_attribution")
validate_manifest = load("validate_manifest")
validate_items = load("validate_items")
validate_golden = load("validate_golden")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def test_repo_itself_passes_all_checks():
    root = SCRIPTS.parent
    assert check_attribution.check(root) == []
    assert validate_manifest.check(root) == []
    assert validate_golden.check(root) == []
    assert validate_items.check(root) == []


def test_attribution_flags_missing_credit(tmp_path):
    (tmp_path / "README.md").write_text("# Project", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('authors = [{name = "Samputhy Khim"}]')
    (tmp_path / "CITATION.cff").write_text("family-names: Khim\ngiven-names: Samputhy\n")
    assert check_attribution.check(tmp_path) == ["README.md: does not credit 'Samputhy Khim'"]


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            {"source": "s", "license": "CC-BY-4.0", "retrieved": "2026-09-30", "transform": "none"},
            0,
        ),
        ({"source": "s", "license": "CC-BY-4.0", "retrieved": "2026-09-30"}, 1),
        ({"source": "s", "license": "CC-BY-4.0", "retrieved": "30/09/2026", "transform": "x"}, 1),
    ],
)
def test_manifest_records(tmp_path, record, expected):
    write_jsonl(tmp_path / "data" / "web" / "manifest.jsonl", [record])
    assert len(validate_manifest.check(tmp_path)) == expected


def test_unverified_test_item_fails(tmp_path):
    write_jsonl(tmp_path / "bench" / "rc" / "test.jsonl", [{"id": 1, "verified": False}])
    errors = validate_items.check(tmp_path)
    assert any("not verified" in e for e in errors)


def test_drafts_are_not_checked(tmp_path):
    write_jsonl(tmp_path / "bench" / "drafts" / "test.jsonl", [{"id": 1, "verified": False}])
    assert validate_items.check(tmp_path) == []


def test_canary_required_once_defined(tmp_path):
    (tmp_path / "bench").mkdir()
    (tmp_path / "bench" / "CANARY").write_text("canary-guid-1234\n")
    item = {"id": 1, "verified": True, "verified_by": "a1", "verified_at": "2026-09-30"}
    write_jsonl(tmp_path / "bench" / "rc" / "test.jsonl", [item])
    assert validate_items.check(tmp_path) == ["bench/rc/test.jsonl: missing canary string"]

    write_jsonl(tmp_path / "bench" / "rc" / "test.jsonl", [{"canary": "canary-guid-1234"}, item])
    assert validate_items.check(tmp_path) == []


GOLDEN_OK = {
    "id": "G-0001",
    "input": "abc",
    "expected": "abc",
    "source": "https://example.org/page",
    "license": "CC-BY-4.0",
    "retrieved": "2026-09-30",
    "transform": "none",
    "verified_by": "reviewer-1",
    "verified_at": "2026-09-30",
}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({}, None),
        ({"verified_by": ""}, "verified_by"),
        ({"verified_at": "yesterday"}, "verified_at"),
        ({"id": "7"}, "'id'"),
        ({"license": ""}, "license"),
        ({"input": "ask @someone"}, "handle or email"),
        ({"expected": "mail me a@b.org"}, "handle or email"),
        ({"options": {"strip": True}}, "options"),
    ],
)
def test_golden_records(tmp_path, change, message):
    write_jsonl(tmp_path / "tests" / "golden" / "normalization.jsonl", [{**GOLDEN_OK, **change}])
    errors = validate_golden.check(tmp_path)
    if message is None:
        assert errors == []
    else:
        assert len(errors) == 1 and message in errors[0]


def test_golden_ids_are_unique_and_drafts_skipped(tmp_path):
    write_jsonl(tmp_path / "tests" / "golden" / "a.jsonl", [GOLDEN_OK, GOLDEN_OK])
    write_jsonl(tmp_path / "tests" / "golden" / "drafts" / "d.jsonl", [{"id": "draft"}])
    assert [e for e in validate_golden.check(tmp_path) if "duplicate" in e] != []
    assert len(validate_golden.check(tmp_path)) == 1


def test_golden_draft_round_trip(tmp_path, monkeypatch, capsys):

    monkeypatch.syspath_prepend(str(SCRIPTS))
    golden_draft = load("golden_draft")
    monkeypatch.chdir(tmp_path)
    misordered = "".join(map(chr, (0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A)))
    (tmp_path / "lines.txt").write_text(f"{misordered}\nsee @someone\n\n", encoding="utf-8")
    out = tmp_path / "tests" / "golden" / "drafts" / "d.jsonl"
    args = ["lines.txt", "--source", "s", "--license", "CC-BY-4.0", "--retrieved"]
    args += ["2026-09-30", "--transform", "none", "--out", str(out)]
    assert golden_draft.main(args) == 0
    assert "handle or email" in capsys.readouterr().err
    [draft] = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert draft["id"] == "G-0001"
    assert draft["expected"] == "".join(map(chr, (0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A)))
    assert draft["rules"] == ["2.2"]
    # A draft is not golden until a person verifies it.
    promoted = {**draft, "verified_by": "reviewer-1", "verified_at": "2026-09-30"}
    assert validate_golden.check_fixture(draft, "d") != []
    assert validate_golden.check_fixture(promoted, "d") == []


def test_sentence_split_and_review_page(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    drafting = load("draft_wikipedia_fixtures")
    review = load("review_drafts")
    ka, khan = "ក", "។"
    text = f"{ka * 10}{khan}{ka * 12}\nshort\nmail a@b.org {ka * 10}"
    assert drafting.sentences(text) == [ka * 10 + khan, ka * 12]
    draft = {
        "id": "G-0001",
        "input": "ក្ដ",
        "rules": ["3.8"],
        "source": "https://example.org",
    }
    drafts = tmp_path / "d.jsonl"
    drafts.write_text(json.dumps(draft) + "\n", encoding="utf-8")
    page = tmp_path / "review.html"
    assert review.main([str(drafts), "--html", str(page)]) == 0
    content = page.read_text(encoding="utf-8")
    assert 'id="G-0001"' in content
    assert "1780 17D2 178A → 1780 17D2 178F" in content


def test_lunar_probe_counts_and_samples(tmp_path, capsys):
    import gzip

    probe = load("lunar_probe")
    lunar = "".join(map(chr, (0x17E1, 0x17E5, 0x17D2, 0x17D4)))
    with gzip.open(tmp_path / "a.txt.gz", "wt", encoding="utf-8") as handle:
        handle.write(f"x {lunar} y\nno match\n")
    (tmp_path / "b.jsonl").write_text(json.dumps({"text": f"{lunar}\n{lunar}"}) + "\n")
    out = tmp_path / "sample.jsonl"
    assert (
        probe.main([str(tmp_path / "a.txt.gz"), str(tmp_path / "b.jsonl"), "--out", str(out)]) == 0
    )
    assert "matches: 3" in capsys.readouterr().out
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3
    assert rows[0]["before"] == "x " and rows[0]["after"] == " y"


def test_tokenizer_stats_with_char_tokenizer(tmp_path):
    stats = load("tokenizer_stats")
    misordered = "".join(map(chr, (0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A)))
    (tmp_path / "p.tsv").write_text(f"{misordered}\tKhmer\n", encoding="utf-8")
    result = stats.measure(len, stats.read_pairs(tmp_path / "p.tsv"))
    assert result["km_tokens"] == result["km_tokens_normalized"] == 5
    assert result["sentences_changed_by_normalize"] == 1
    assert result["km_tokens_per_syllable"] == 2.5  # two clusters: the syllable and RO
    assert result["parity"] == 1.0  # "Khmer" is five characters too


def test_landscape_license_groups():
    render = load("render_landscape")
    assert render.group("MIT") == "Permissive"
    assert render.group("CC0 (packaging only)") == "Permissive"
    assert render.group("cc-by-sa-3.0, gfdl") == "Share-alike or copyleft"
    assert render.group("CC-BY-NC-4.0") == "Non-commercial"
    assert render.group("other (license_name: seallms)") == "Custom, mixed or by agreement"
    assert render.group("unknown") == "Unknown (no license found)"


def test_tokenizer_stats_line_aligned_files(tmp_path, capsys):
    stats = load("tokenizer_stats")
    (tmp_path / "km.txt").write_text("កា\nខ\n", encoding="utf-8")
    (tmp_path / "en.txt").write_text("ka\nkha\n", encoding="utf-8")
    args = ["--km", str(tmp_path / "km.txt"), "--en", str(tmp_path / "en.txt")]
    assert stats.main([*args, "--tokenizer", "chars"]) == 0
    assert "2 sentence pairs" in capsys.readouterr().out
    (tmp_path / "en.txt").write_text("ka\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        stats.main([*args, "--tokenizer", "chars"])


def test_encoding_variants_counts(tmp_path, monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    variants = load("encoding_variants")
    canonical = "ខ្មែ"
    misordered = "ខែ្ម"
    (tmp_path / "a.txt").write_text(f"{canonical} {canonical} {misordered}\n", encoding="utf-8")
    assert variants.main([str(tmp_path), "--top", "1"]) == 0
    out = capsys.readouterr().out
    assert "syllables seen in 2+ encodings: 1; their tokens: 3" in out
    assert "tokens not in canonical form: 1 (33.33%)" in out


def test_task_lock_requires_version_bump():
    lock_tasks = load("lock_tasks")
    locked = {"t": {"version": "1", "prompt_sha256": "old"}}
    assert lock_tasks.problems(locked, {"t": {"version": "1", "prompt_sha256": "new"}})
    assert not lock_tasks.problems(locked, {"t": {"version": "2", "prompt_sha256": "new"}})
    assert not lock_tasks.problems(locked, {"u": {"version": "1", "prompt_sha256": "x"}})


def test_bench_task_specs_load():
    from pheasa.bench.runner import load_task

    root = SCRIPTS.parent / "bench" / "tasks"
    tasks = [load_task(path) for path in sorted(root.glob("*.toml"))]
    assert len(tasks) == 8
    for task in tasks:
        assert (root / f"{task.name}.md").exists()
        assert "en" in task.prompts, task.name
        for prompt in task.prompts.values():
            assert {f for _, f, _, _ in string.Formatter().parse(prompt) if f}, task.name


def test_review_items_page(tmp_path):
    review = load("review_items")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    item = {
        "id": "numbers-and-dates-d001",
        "input": {"instruction_en": "Convert", "instruction_km": "x", "text": "7"},
        "reference": ["៧", "7"],
        "notes": "n",
        "source": "https://example.org",
    }
    (drafts / "numbers-and-dates.jsonl").write_text(json.dumps(item) + "\n", encoding="utf-8")
    (drafts / "prompts-km.toml").write_text('[numbers-and-dates]\nkm = """{text}"""\n', "utf-8")
    page = tmp_path / "pick.html"
    assert (
        review.main(
            [str(drafts), "--tasks", str(SCRIPTS.parent / "bench" / "tasks"), "--html", str(page)]
        )
        == 0
    )
    content = page.read_text(encoding="utf-8")
    assert 'id="numbers-and-dates-d001"' in content and 'id="prompt-numbers-and-dates"' in content
    assert "៧ | 7" in content and 'value="drop"' in content
