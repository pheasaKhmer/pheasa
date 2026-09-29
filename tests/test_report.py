"""Tests for the validation step of spec/normalization.md: validate() and report=True."""

import pytest
from _oracle import load_oracle
from hypothesis import given, settings
from hypothesis import strategies as st
from test_normalize import cps, khmer_text, nfc, u_cluster, wellformed_text
from test_options import option_text, options

from pheasa import Change, Issue, Report, normalize, validate

oracle = load_oracle()
GRAMMAR_CODES = {"V1", "V2", "V3", "V4", "V5", "V6"}
RULES = {"1.1", "1.3", "2.2", *(f"3.{n}" for n in range(1, 10)), "4.zwsp", "4.digits"}
RULES |= {"4.deprecated"}
# Characters that make NFC act across more than one character: Hangul jamo compose,
# 0B47 + 0B3E compose, 212B is a singleton, 0344 and 0F73 decompose to marks.
TRICKY_NFC = [*"\u1100\u1161\u11a8\u0b47\u0b3e\u212b\u0344\u0f73\u0301\u0334a"]
tricky_text = st.lists(
    st.sampled_from([*TRICKY_NFC, "\u1780", "\u17b6", "\u17d2", "\u17dd", "\u200b"]), max_size=16
).map("".join)
any_text = st.one_of(option_text, khmer_text, wellformed_text, u_cluster, tricky_text)


def codes(text: str) -> list[str]:
    return [issue.code for issue in validate(text)]


# --- validate() -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "text"),
    [
        ("V1", cps(0x1780, 0x17D2)),
        ("V1", cps(0x1780, 0x17D2, 0x0020, 0x1781)),
        ("V2", cps(0x1780, 0x200C, 0x17B6)),
        # ZWNJ after a triisap that would not downshift anyway (no above vowel)
        ("V2", cps(0x179F, 0x17CA, 0x200C, 0x17B6)),
        ("V3", cps(0x1780, 0x17B6, 0x200D)),
        ("V3", cps(0x1780, 0x17BB, 0x200D, 0x17D2, 0x1794)),
        ("V4", cps(0x1780, 0x17B6, 0x17B6)),
        # 17C4 17B8 is Middle Khmer (the output of rule 3.2), not Modern Khmer
        ("V4", cps(0x1780, 0x17C4, 0x17B8)),
        ("V4", cps(0x1794, 0x17D2, 0x1780, 0x17BB, 0x17B7)),
        ("V4", cps(0x1780, 0x17D2, 0x1781, 0x17D2, 0x1782, 0x17D2, 0x1783)),
        ("V5", cps(0x0020, 0x17B6)),
        ("V5", cps(0x17DD)),
        ("V6", cps(0x17E1, 0x17E0, 0x17D2, 0x17D4)),
        ("V6", cps(0x17D4, 0x17D2, 0x17E1)),
        ("V7", cps(0x1780, 0x17D3)),
        ("V8", cps(0x1780, 0xFEFF, 0x1781)),
    ],
)
def test_validate_flags(code, text):
    assert code in codes(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello, world",
        cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A),
        cps(0x1780, 0x17CC, 0x17D2, 0x1781, 0x17D2, 0x179A, 0x17CA, 0x17B6, 0x17C6, 0x17C7),
        # ZWNJ where it keeps a triisap up (UTN #61 p. 16)
        cps(0x179F, 0x17CA, 0x200C, 0x17B7),
        cps(0x1798, 0x17C9, 0x200C, 0x17D0),
        # Other characters stand alone, and so does U+17D3 apart from its own flag (V7)
        cps(0x17D4, 0x17A3, 0x17B4, 0x17E1),
        # ZWJ in an emoji sequence is not Khmer's business
        "\U0001f469‍\U0001f4bb",
        cps(0xFEFF, 0x1780),
    ],
)
def test_validate_accepts(text):
    assert codes(text) == []


@settings(max_examples=2000)
@given(khmer_text)
def test_validate_is_at_least_as_strict_as_khtest(text):
    for normalized in (oracle.khnormal(nfc(text)), normalize(text)):
        flagged = [i for i in validate(normalized) if i.code in GRAMMAR_CODES]
        if oracle.khtest(normalized) is not None:
            assert flagged
        else:
            # khtest accepts any of U+17D3-17FF, ZWNJ and ZWJ as a standalone syllable;
            # UTN #61 p. 16 does not (spec "Validation", differences from khtest).
            assert all(normalized[i.start] in "៝‌‍" for i in flagged)


@settings(max_examples=500)
@given(any_text)
def test_validate_issues_are_ordered_and_in_range(text):
    issues = validate(text)
    assert list(issues) == sorted(issues, key=lambda i: (i.start, i.code))
    assert all(0 <= i.start < i.end <= len(text) for i in issues)


# --- normalize(report=True) -----------------------------------------------------------


def test_report_example():
    text = cps(0xFEFF, 0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A, 0x200B, 0x1780, 0x17D2, 0x178A)
    report = normalize(text, report=True, zwsp="space")
    assert isinstance(report, Report)
    assert report.text == cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A, 0x20, 0x1780, 0x17D2, 0x178F)
    assert report.changes == (
        Change(("1.1",), 0, 1, cps(0xFEFF), "", 0),
        Change(
            ("2.2",),
            1,
            5,
            cps(0x1781, 0x17C2, 0x17D2, 0x1798),
            cps(0x1781, 0x17D2, 0x1798, 0x17C2),
            0,
        ),
        Change(("4.zwsp",), 6, 7, cps(0x200B), " ", 5),
        Change(("3.8",), 7, 10, cps(0x1780, 0x17D2, 0x178A), cps(0x1780, 0x17D2, 0x178F), 6),
    )
    assert report.issues == ()


def test_report_names_every_rule_in_a_cluster():
    # 3.5 then 3.6 in one cluster, plus a sort
    report = normalize(cps(0x179F, 0x17BE, 0x17BB), report=True)
    assert report.text == cps(0x179F, 0x17CA, 0x17BE)
    assert report.changes[0].rules == ("3.5", "3.6")


def test_report_flags_cluster_left_as_typed():
    text = cps(0x1780, 0x17D2, 0x17CC, 0x1781, 0x17CC)
    report = normalize(text, report=True)
    assert report.text == text
    assert report.changes == ()
    assert Issue("V9", 0, 3, "cluster left as typed (rule 2.3)") in report.issues


def test_report_tracks_nfc():
    report = normalize("é", report=True)
    assert report.changes == (Change(("1.3",), 0, 2, "é", "é", 0),)


@pytest.mark.parametrize("text", ["a\u0301\u0f73\u0334", "\u1100\u1161\u11a8", "\u212b\u0301"])
def test_report_nfc_segments(text):
    # Regression: U+0F73 has ccc 0 but decomposes to marks, so it cannot start a segment.
    report = normalize(text, report=True)
    assert report.text == normalize(text)
    assert all(change.rules == ("1.3",) for change in report.changes)


def test_report_rejects_bad_options():
    with pytest.raises(ValueError, match="zwsp"):
        normalize("", report=True, zwsp="remove")


@settings(max_examples=1000)
@given(any_text, options)
def test_report_text_equals_normalize(text, opts):
    assert normalize(text, report=True, **opts).text == normalize(text, **opts)


@settings(max_examples=1000)
@given(any_text, options)
def test_report_changes_rebuild_the_output(text, opts):
    report = normalize(text, report=True, **opts)
    rebuilt, done = [], 0
    for change in report.changes:
        assert change.start >= done
        assert change.before == text[change.start : change.end] != change.after
        assert change.rules and set(change.rules) <= RULES
        rebuilt += (text[done : change.start], change.after)
        done = change.end
        position = change.output_start
        assert report.text[position : position + len(change.after)] == change.after
    rebuilt.append(text[done:])
    assert "".join(rebuilt) == report.text


@settings(max_examples=500)
@given(any_text, options)
def test_report_issues_are_validate_plus_rule_2_3(text, opts):
    report = normalize(text, report=True, **opts)
    assert [i for i in report.issues if i.code != "V9"] == list(validate(report.text))


def test_validate_accepts_dotted_circle_after_coeng():
    # Regression: SIL khtest's COENG pattern takes U+25CC as the subscript base.
    assert codes(cps(0x1780, 0x17D2, 0x25CC)) == []
