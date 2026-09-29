"""Smoke tests pinning the SIL khnormal oracle's behavior on documented cases.

Each case cites the rule in spec/normalization.md it exercises. If an upstream update
changes any of these, the spec needs review before the oracle is bumped.
"""

import hashlib
import importlib.util
from pathlib import Path

import pytest

ORACLE = Path(__file__).resolve().parent / "oracle" / "khnormal_sil.py"
ORACLE_SHA256 = "3cf799b41e09bea3603f5c4c5c7c5faf951d744fe0249bc90a0020126ad91e6d"


def load_oracle():
    spec = importlib.util.spec_from_file_location("khnormal_sil", ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load_oracle()


def cps(*code_points: int) -> str:
    return "".join(map(chr, code_points))


def test_oracle_file_is_unmodified():
    assert hashlib.sha256(ORACLE.read_bytes()).hexdigest() == ORACLE_SHA256


@pytest.mark.parametrize(
    ("rule", "source", "expected"),
    [
        # Stage 2: vowel typed before the subscript (README example)
        (
            "2",
            cps(0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A),
            cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A),
        ),
        # Stage 2 / C1: shifter moves after the coeng
        (
            "C1",
            cps(0x1798, 0x17C9, 0x17D2, 0x1784, 0x17C3),
            cps(0x1798, 0x17D2, 0x1784, 0x17C9, 0x17C3),
        ),
        ("3.1", cps(0x1780, 0x17D2, 0x17D2, 0x1798), cps(0x1780, 0x17D2, 0x1798)),
        ("3.2", cps(0x1780, 0x17BE, 0x17B6), cps(0x1780, 0x17C4, 0x17B8)),
        ("3.3", cps(0x1780, 0x17C1, 0x17B8), cps(0x1780, 0x17BE)),
        ("3.4", cps(0x1780, 0x17C1, 0x17B6), cps(0x1780, 0x17C4)),
        ("3.6", cps(0x179F, 0x17BB, 0x17B8), cps(0x179F, 0x17CA, 0x17B8)),
        (
            "3.7",
            cps(0x179F, 0x17D2, 0x179A, 0x17D2, 0x1780),
            cps(0x179F, 0x17D2, 0x1780, 0x17D2, 0x179A),
        ),
        ("3.8", cps(0x1780, 0x17D2, 0x178A), cps(0x1780, 0x17D2, 0x178F)),
    ],
)
def test_oracle_applies_rule(rule, source, expected):
    assert oracle.khnormal(source) == expected


@pytest.mark.parametrize(
    ("case", "text"),
    [
        ("dangling coeng", cps(0x1780, 0x17D2)),
        ("stray ZWNJ", cps(0x1780, 0x200C, 0x17B6)),
        ("repeated vowel", cps(0x1780, 0x17B6, 0x17B6)),
        ("legacy lunar date (not converted, see Q-006)", cps(0x17E1, 0x17E0, 0x17D2, 0x17D4)),
    ],
)
def test_oracle_leaves_unfixable_text_unchanged_but_flags_it(case, text):
    assert oracle.khnormal(text) == text
    assert oracle.khtest(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A),  # already canonical
        cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A, 0x200B, 0x1797, 0x17B6, 0x179F, 0x17B6),  # ZWSP
        cps(0x17A3),  # deprecated characters are Other: untouched
    ],
)
def test_oracle_leaves_canonical_text_unchanged(text):
    assert oracle.khnormal(text) == text
