"""Golden fixtures: real text whose normalized form a native speaker has verified.

Records live in tests/golden/*.jsonl (format in tests/golden/README.md) and are checked
by scripts/validate_golden.py. Any change to these outputs needs a new
NORMALIZATION_VERSION, a CHANGELOG entry and a DECISIONS entry.
"""

import json
from pathlib import Path

import pytest

from pheasa import normalize

GOLDEN = Path(__file__).resolve().parent / "golden"
FIXTURES = [
    json.loads(line)
    for path in sorted(GOLDEN.glob("*.jsonl"))
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_golden_fixture(fixture):
    options = fixture.get("options", {})
    assert normalize(fixture["input"], **options) == fixture["expected"]
    # Verified output is already normalized.
    assert normalize(fixture["expected"], **options) == fixture["expected"]
