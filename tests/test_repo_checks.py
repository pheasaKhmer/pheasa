import importlib.util
import json
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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def test_repo_itself_passes_all_checks():
    root = SCRIPTS.parent
    assert check_attribution.check(root) == []
    assert validate_manifest.check(root) == []
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
