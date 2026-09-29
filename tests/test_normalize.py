"""Tests for Stages 1 and 2 of spec/normalization.md.

Test requirement numbers refer to the spec's "Test requirements" section.
"""

import unicodedata
from collections import Counter
from itertools import pairwise

import pytest
from _oracle import load_oracle_sort
from hypothesis import given, settings
from hypothesis import strategies as st

import pheasa
from pheasa import normalize

oracle_sort = load_oracle_sort()

BOM = "\ufeff"
COENG = "\u17d2"
ZWNJ = "\u200c"
ZWJ = "\u200d"
ZWSP = "\u200b"


def cps(*code_points: int) -> str:
    return "".join(map(chr, code_points))


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def chars(first: int, last: int) -> list[str]:
    return [chr(cp) for cp in range(first, last + 1)]


CONSONANTS = chars(0x1780, 0x17A2)
BASES = CONSONANTS + chars(0x17A5, 0x17B3)
BASE_SET = frozenset(BASES)
KHMER = chars(0x1780, 0x17FF) + chars(0x19E0, 0x19FF)
# Everything a cluster can contain, plus separators and look-alike placeholders.
KHMER_TEXT_ALPHABET = [*KHMER, ZWNJ, ZWJ, ZWSP, " ", "\u25cc", "a"]
# Non-Khmer characters that NFC reorders or composes, spread over many combining classes.
NFC_PROBES = [
    "\u0300",  # ccc 230
    "\u0301",  # ccc 230, composes with "e"
    "\u0316",  # ccc 220
    "\u0334",  # ccc 1
    "\u093c",  # ccc 7
    "\u05b0",  # ccc 10
    "\u0e48",  # ccc 107
    "e",
    "\u00e9",
    BOM,
]
MIXED_ALPHABET = KHMER_TEXT_ALPHABET + NFC_PROBES

khmer_text = st.lists(st.sampled_from(KHMER_TEXT_ALPHABET), max_size=24).map("".join)
mixed_text = st.lists(st.sampled_from(MIXED_ALPHABET), max_size=24).map("".join)

# One token per Stage 2 sort key. Joiner units (COENG + base, ZWJ + COENG + consonant)
# are atomic, so every COENG and ZWJ is followed by what it joins.
TOKENS_BY_KEY = {
    "robat": st.just("\u17cc"),
    "coeng": st.sampled_from(BASES).map(lambda b: COENG + b),
    "shifter": st.sampled_from(chars(0x17C9, 0x17CA)),
    "zwnj": st.just(ZWNJ),
    "vowel_pre": st.sampled_from(chars(0x17BE, 0x17C5)),
    "vowel_below": st.sampled_from(chars(0x17BB, 0x17BD)),
    "vowel_above": st.sampled_from(chars(0x17B7, 0x17BA)),
    "vowel_post": st.just("\u17b6"),
    "modifier": st.sampled_from([*chars(0x17C6, 0x17C6), "\u17cb", *chars(0x17CD, 0x17D1)]),
    "final": st.sampled_from(chars(0x17C7, 0x17C8)),
    "final_coeng": st.sampled_from(CONSONANTS).map(lambda c: ZWJ + COENG + c),
}
any_token = st.one_of(*TOKENS_BY_KEY.values(), st.just("\u17d3"), st.just("\u17dd"))
wellformed_cluster = st.builds(
    lambda base, tokens: base + "".join(tokens),
    st.sampled_from(BASES),
    st.lists(any_token, max_size=6),
)
wellformed_text = st.lists(
    st.one_of(wellformed_cluster, st.sampled_from([" ", ZWSP, "\u17d4", "a"])),
    max_size=6,
).map("".join)


def cluster_bases(text: str) -> list[str]:
    """Bases that start a cluster: a base not joined to the COENG or ZWJ before it."""
    return [
        ch
        for i, ch in enumerate(text)
        if ch in BASE_SET and (i == 0 or text[i - 1] not in (COENG, ZWJ))
    ]


def joined_pairs(text: str) -> int:
    """Count COENG or ZWJ characters directly followed by a base."""
    return sum(1 for a, b in pairwise(text) if a in (COENG, ZWJ) and b in BASE_SET)


# --- Examples -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rule", "source", "expected"),
    [
        # Stage 2 example (README): vowel typed before the subscript
        (
            "2.2",
            cps(0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A),
            cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A),
        ),
        # Conflict C1: shifter moves after the coeng
        (
            "C1",
            cps(0x1798, 0x17C9, 0x17D2, 0x1784, 0x17C3),
            cps(0x1798, 0x17D2, 0x1784, 0x17C9, 0x17C3),
        ),
        # Robat before coeng, ZWNJ after shifter, modifier before final
        (
            "2.2",
            cps(0x1780, 0x17C7, 0x17B6, 0x200C, 0x17CA, 0x17D2, 0x1781, 0x17CC),
            cps(0x1780, 0x17CC, 0x17D2, 0x1781, 0x17CA, 0x200C, 0x17B6, 0x17C7),
        ),
        # Same key keeps typed order: two above vowels are not swapped
        ("2.2", cps(0x1780, 0x17B8, 0x17B7), cps(0x1780, 0x17B8, 0x17B7)),
        # A final coeng (ZWJ unit) sorts last
        (
            "2.2",
            cps(0x1780, 0x200D, 0x17D2, 0x1781, 0x17B6),
            cps(0x1780, 0x17B6, 0x200D, 0x17D2, 0x1781),
        ),
        ("1.1", cps(0xFEFF, 0x1780), cps(0x1780)),
        ("1.1", cps(0xFEFF, 0xFEFF, 0x1780), cps(0x1780)),
        ("1.2", cps(0x1780, 0xFEFF, 0x1781), cps(0x1780, 0xFEFF, 0x1781)),
        ("1.3", "e\u0301", "\u00e9"),
        # NFC puts COENG (ccc 9) before ATTHACAN (ccc 230), which detaches the subscript.
        ("1.3", cps(0x1780, 0x17DD, 0x17D2, 0x179A), cps(0x1780, 0x17D2, 0x17DD, 0x179A)),
        # ZWSP ends a cluster and is kept
        ("2.1", cps(0x1780, 0x200B, 0x17B6), cps(0x1780, 0x200B, 0x17B6)),
        # A dotted circle is not a cluster start
        ("2.1", cps(0x25CC, 0x17B6, 0x17D2, 0x1781), cps(0x25CC, 0x17B6, 0x17D2, 0x1781)),
        # Marks with no base before them are left alone
        ("2.1", cps(0x0041, 0x17B6, 0x17D2, 0x1780), cps(0x0041, 0x17B6, 0x17D2, 0x1780)),
        # Deprecated characters are Other: untouched
        ("2.1", cps(0x17A3, 0x17B6), cps(0x17A3, 0x17B6)),
    ],
)
def test_example(rule, source, expected):
    assert normalize(source) == expected


@pytest.mark.parametrize(
    "text",
    [
        # Sorting would move the stray ZWJ last, next to the next syllable's base.
        cps(0x1780, 0x200D, 0x17B6, 0x1781, 0x17C9),
        # Sorting would move the dangling coeng last, next to the next syllable's base.
        cps(0x1780, 0x17D2, 0x17CC, 0x1781, 0x17CC),
        # Sorting would put ATTHACAN (ccc 230) before U+0316 (ccc 220), which NFC swaps.
        cps(0x1780, 0x17DD, 0x17B6, 0x0316),
    ],
)
def test_unstable_cluster_is_left_as_typed(text):
    # Rule 2.3. The oracle differs here; see the spec's "Differences from the oracle".
    assert oracle_sort(nfc(text)) != text
    assert normalize(text) == text


def test_public_api():
    assert pheasa.normalize is normalize
    assert pheasa.NORMALIZATION_VERSION == "0"


# --- Properties -----------------------------------------------------------------------


@settings(max_examples=1000)
@given(wellformed_text)
def test_matches_oracle_sort_on_wellformed_clusters(text):
    # Requirement 1 for Stage 2: no exceptions when every joiner is followed by its unit.
    assert normalize(text) == oracle_sort(nfc(text))


@settings(max_examples=2000)
@given(khmer_text)
def test_matches_oracle_sort_on_any_khmer_text(text):
    # Requirement 1 for Stage 2. The only allowed difference is rule 2.3 (a joiner at
    # the end of a sorted cluster), which shows up as a new joiner + base pair in the
    # oracle's output.
    cleaned = nfc(text)
    expected = oracle_sort(cleaned)
    if normalize(text) != expected:
        assert joined_pairs(expected) > joined_pairs(cleaned)


@settings(max_examples=1000)
@given(mixed_text)
def test_idempotent(text):
    # Requirement 2
    once = normalize(text)
    assert normalize(once) == once


@settings(max_examples=1000)
@given(mixed_text)
def test_nfc_invariant(text):
    # Requirement 3
    once = normalize(text)
    assert nfc(once) == once


@settings(max_examples=1000)
@given(khmer_text)
def test_no_lost_bases(text):
    # Requirement 4. After Stage 1 (NFC; this alphabet has no BOM), Stage 2 only
    # reorders: every character survives and cluster-starting bases keep their order.
    cleaned = nfc(text)
    once = normalize(text)
    assert Counter(once) == Counter(cleaned)
    assert cluster_bases(once) == cluster_bases(cleaned)


@given(
    st.sampled_from(BASES),
    st.lists(st.sampled_from(sorted(TOKENS_BY_KEY)), unique=True).flatmap(
        lambda keys: st.tuples(*(TOKENS_BY_KEY[k] for k in keys))
    ),
    st.randoms(use_true_random=False),
)
def test_typing_order_of_distinct_keys_does_not_matter(base, tokens, rnd):
    # Requirement 5, restricted to Stage 2: tokens with different sort keys can be typed
    # in any order. (Whether two orders render alike is a separate, human question.)
    shuffled = list(tokens)
    rnd.shuffle(shuffled)
    assert normalize(base + "".join(shuffled)) == normalize(base + "".join(tokens))
