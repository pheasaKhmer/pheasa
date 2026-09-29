"""Tests for Stage 4 of spec/normalization.md (opt-in options)."""

import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_normalize import (
    BASE_SET,
    MIXED_ALPHABET,
    ZWSP,
    cluster_bases,
    cps,
    wellformed_text,
)

from pheasa import normalize

KHMER_DIGITS = "".join(chr(0x17E0 + d) for d in range(10))
LEK_ATTAK = "".join(chr(0x17F0 + d) for d in range(10))
DEPRECATED = "ឣឤ឴឵៘"
OPTION_ALPHABET = [*MIXED_ALPHABET, *"0123456789", ZWSP, ZWSP]

option_text = st.one_of(
    st.lists(st.sampled_from(OPTION_ALPHABET), max_size=24).map("".join),
    wellformed_text,
)
options = st.fixed_dictionaries(
    {
        "zwsp": st.sampled_from(["keep", "strip", "space"]),
        "digits": st.sampled_from(["keep", "khmer", "ascii"]),
        "fold_deprecated": st.booleans(),
        "preserve_coeng_da": st.booleans(),
    }
)


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


@pytest.mark.parametrize(
    ("options", "source", "expected"),
    [
        ({"zwsp": "strip"}, cps(0x1780, 0x200B, 0x1781), cps(0x1780, 0x1781)),
        ({"zwsp": "space"}, cps(0x1780, 0x200B, 0x1781), cps(0x1780, 0x20, 0x1781)),
        ({"digits": "ascii"}, KHMER_DIGITS, "0123456789"),
        ({"digits": "khmer"}, "0123456789", KHMER_DIGITS),
        # LEK ATTAK divination numerals are never converted
        ({"digits": "ascii"}, LEK_ATTAK, LEK_ATTAK),
        ({"fold_deprecated": True}, cps(0x17A3), cps(0x17A2)),
        ({"fold_deprecated": True}, cps(0x17A4), cps(0x17A2, 0x17B6)),
        ({"fold_deprecated": True}, cps(0x17D8), cps(0x17D4, 0x179B, 0x17D4)),
        ({"fold_deprecated": True}, cps(0x1780, 0x17B4, 0x17B6), cps(0x1780, 0x17B6)),
        ({"fold_deprecated": True}, cps(0x1780, 0x17B5), cps(0x1780)),
        # Options run before Stage 2: removing ZWSP joins the coeng to its base
        (
            {"zwsp": "strip"},
            cps(0x1780, 0x17B6, 0x17D2, 0x200B, 0x1781),
            cps(0x1780, 0x17D2, 0x1781, 0x17B6),
        ),
        # ... and before NFC: removing 17B4 exposes <17DD 17D2>, which NFC reorders
        (
            {"fold_deprecated": True},
            cps(0x1780, 0x17DD, 0x17B4, 0x17D2, 0x1781),
            cps(0x1780, 0x17D2, 0x17DD, 0x1781),
        ),
    ],
)
def test_option_example(options, source, expected):
    assert normalize(source, **options) == expected


@pytest.mark.parametrize(
    ("option", "value"),
    [("zwsp", "remove"), ("zwsp", None), ("digits", "latin"), ("digits", True)],
)
def test_invalid_option_is_rejected(option, value):
    with pytest.raises(ValueError, match=option):
        normalize("", **{option: value})


@settings(max_examples=500)
@given(option_text)
def test_defaults_keep_zwsp_digits_and_deprecated_characters(text):
    once = normalize(text)
    for ch in (ZWSP, *KHMER_DIGITS, *"0123456789", *DEPRECATED):
        assert once.count(ch) == nfc(text).count(ch)


@settings(max_examples=1000)
@given(option_text, options)
def test_idempotent_with_options(text, opts):
    once = normalize(text, **opts)
    assert normalize(once, **opts) == once


@settings(max_examples=1000)
@given(option_text, options)
def test_nfc_invariant_with_options(text, opts):
    once = normalize(text, **opts)
    assert nfc(once) == once


@settings(max_examples=500)
@given(option_text, options)
def test_options_do_what_they_say(text, opts):
    once = normalize(text, **opts)
    if opts["zwsp"] != "keep":
        assert ZWSP not in once
    if opts["digits"] == "khmer":
        assert not any(c in once for c in "0123456789")
    if opts["digits"] == "ascii":
        assert not any(c in once for c in KHMER_DIGITS)
    if opts["fold_deprecated"]:
        assert not any(c in once for c in DEPRECATED)


@settings(max_examples=500)
@given(option_text)
def test_zwsp_and_digit_options_keep_bases(text):
    # Requirement 4 holds for every option except fold_deprecated: bases survive.
    # ZWSP removal can join a dangling coeng to the next base, so compare base counts.
    kept = normalize(text, preserve_coeng_da=True, zwsp="strip", digits="ascii")
    before = [c for c in nfc(text) if c in BASE_SET]
    assert sorted(c for c in kept if c in BASE_SET) == sorted(before)
    assert len(cluster_bases(normalize(text, zwsp="space"))) == len(cluster_bases(nfc(text)))
