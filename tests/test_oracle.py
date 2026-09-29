"""Smoke tests pinning the SIL khnormal oracle's behavior on documented cases.

Each case cites the rule in spec/normalization.md it exercises. If an upstream update
changes any of these, the spec needs review before the oracle is bumped.
"""

import hashlib

import pytest
from _oracle import ORACLE, load_oracle, load_oracle_sort

ORACLE_SHA256 = "3cf799b41e09bea3603f5c4c5c7c5faf951d744fe0249bc90a0020126ad91e6d"

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
        ("legacy lunar date (not converted, see D-009)", cps(0x17E1, 0x17E0, 0x17D2, 0x17D4)),
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


oracle_sort = load_oracle_sort()


def test_sort_only_oracle_skips_stage_3_folds():
    # Rule 3.8 would turn coeng da into coeng ta; the sort-only copy must not.
    text = cps(0x1780, 0x17D2, 0x178A)
    assert oracle.khnormal(text) != text
    assert oracle_sort(text) == text
    # The full oracle is unaffected by loading the sort-only copy.
    assert oracle.khnormal(text) == cps(0x1780, 0x17D2, 0x178F)


def test_oracle_does_not_start_a_cluster_at_dotted_circle():
    # U+25CC is in SIL's `B` pattern but its sort category is Other (spec Stage 2).
    text = cps(0x25CC, 0x17B6, 0x17D2, 0x1781)
    assert oracle_sort(text) == text


@pytest.mark.parametrize(
    ("text", "once", "twice"),
    [
        # A stray ZWJ sorts to the end of its cluster and captures the next base.
        (
            cps(0x1780, 0x200D, 0x17B6, 0x1781, 0x17C9),
            cps(0x1780, 0x17B6, 0x200D, 0x1781, 0x17C9),
            cps(0x1780, 0x17C9, 0x17B6, 0x200D, 0x1781),
        ),
        # A dangling coeng sorts after the robat and captures the next base.
        (
            cps(0x1780, 0x17D2, 0x17CC, 0x1781, 0x17CC),
            cps(0x1780, 0x17CC, 0x17D2, 0x1781, 0x17CC),
            cps(0x1780, 0x17CC, 0x17CC, 0x17D2, 0x1781),
        ),
    ],
)
def test_oracle_sort_is_not_idempotent_when_a_cluster_ends_in_a_joiner(text, once, twice):
    # Spec rule 2.3 exists because of these cases.
    assert oracle_sort(text) == once
    assert oracle_sort(once) == twice
