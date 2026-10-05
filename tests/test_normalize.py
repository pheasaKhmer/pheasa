"""Tests for Stages 1 to 3 of spec/normalization.md.

Test requirement numbers refer to the spec's "Test requirements" section.
"""

import unicodedata
from collections import Counter
from itertools import pairwise

import pytest
from _oracle import load_oracle
from hypothesis import given, settings
from hypothesis import strategies as st

import pheasa
from pheasa import normalize

oracle = load_oracle().khnormal

BOM = "\ufeff"
COENG = "\u17d2"
ZWNJ = "\u200c"
ZWJ = "\u200d"
ZWSP = "\u200b"
BA = "\u1794"
NYO = "\u1789"
ROBAT = "\u17cc"
U = "\u17bb"
SAMYOK_SANNYA = "\u17d0"


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
# are atomic, so every COENG and ZWJ is followed by what it joins. The choices are plain
# lists so that scripts/export_rust_fixtures.py can sample the same tokens.
TOKEN_CHOICES = {
    "robat": ["\u17cc"],
    "coeng": [COENG + b for b in BASES],
    "shifter": chars(0x17C9, 0x17CA),
    "zwnj": [ZWNJ],
    "vowel_pre": chars(0x17BE, 0x17C5),
    "vowel_below": chars(0x17BB, 0x17BD),
    "vowel_above": chars(0x17B7, 0x17BA),
    "vowel_post": ["\u17b6"],
    "modifier": [*chars(0x17C6, 0x17C6), "\u17cb", *chars(0x17CD, 0x17D1)],
    "final": chars(0x17C7, 0x17C8),
    "final_coeng": [ZWJ + COENG + c for c in CONSONANTS],
}
# Marks a well-formed cluster may also contain, outside the per-key tokens.
OTHER_TOKENS = ["\u17d3", "\u17dd"]
SEPARATORS = [" ", ZWSP, "\u17d4", "a"]
# What may follow the -u in a rule 3.6 cluster.
U_FOLLOWERS = [*chars(0x17B6, 0x17C5), "\u17c6", SAMYOK_SANNYA, "\u17dd"]

TOKENS_BY_KEY = {key: st.sampled_from(choices) for key, choices in TOKEN_CHOICES.items()}
any_token = st.one_of(*TOKENS_BY_KEY.values(), *map(st.just, OTHER_TOKENS))
wellformed_cluster = st.builds(
    lambda base, tokens: base + "".join(tokens),
    st.sampled_from(BASES),
    st.lists(any_token, max_size=6),
)
wellformed_text = st.lists(
    st.one_of(wellformed_cluster, st.sampled_from(SEPARATORS)),
    max_size=6,
).map("".join)

# Clusters where rule 3.6 may turn -u into a shifter: consonant cluster, optional
# pre-base vowel, -u, then whatever follows (typed in any order).
u_cluster = st.builds(
    lambda base, robat, coengs, rest: base + robat + "".join(coengs) + U + "".join(rest),
    st.sampled_from(BASES),
    st.sampled_from(["", ROBAT]),
    st.lists(TOKENS_BY_KEY["coeng"], max_size=3),
    st.lists(st.sampled_from(U_FOLLOWERS), max_size=2),
)


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


def u_deviation_possible(text: str) -> bool:
    """Could rule 3.6 differ from the oracle here (spec O5 to O8)? Deliberately broad."""
    return U in text and (
        any(c in text for c in (SAMYOK_SANNYA, NYO, BA))
        or text.count(COENG) >= 3
        or text.count(ROBAT) >= 2
    )


def assert_matches_oracle(text: str) -> None:
    """Test requirement 1: equal to the oracle, or a documented difference applies."""
    cleaned = nfc(text)
    ours, theirs = normalize(text), oracle(cleaned)
    if ours == theirs:
        return
    assert (
        joined_pairs(theirs) > joined_pairs(cleaned)  # O1: rule 2.3
        or oracle(theirs) != theirs  # O4: the oracle's own output is not stable
        or u_deviation_possible(cleaned)  # O5 to O8: rule 3.6
    ), (ours, theirs)


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
        ("3.1", cps(0x1780, 0x17D2, 0x17D2, 0x1798), cps(0x1780, 0x17D2, 0x1798)),
        ("3.1", cps(0x1780, 0x17D2, 0x200C, 0x200D, 0x1798), cps(0x1780, 0x17D2, 0x1798)),
        ("3.2", cps(0x1780, 0x17BE, 0x17B6), cps(0x1780, 0x17C4, 0x17B8)),
        ("3.3", cps(0x1780, 0x17C1, 0x17B8), cps(0x1780, 0x17BE)),
        ("3.3", cps(0x1780, 0x17C1, 0x17BC, 0x17B8), cps(0x1780, 0x17BE, 0x17BC)),
        ("3.4", cps(0x1780, 0x17C1, 0x17B6), cps(0x1780, 0x17C4)),
        # 3.5 then 3.6: <17BE 17BB> after a strong cluster is triisap + 17BE
        ("3.5", cps(0x179F, 0x17BE, 0x17BB), cps(0x179F, 0x17CA, 0x17BE)),
        ("3.6", cps(0x179F, 0x17BB, 0x17B8), cps(0x179F, 0x17CA, 0x17B8)),
        ("3.6", cps(0x1798, 0x17BB, 0x17B8), cps(0x1798, 0x17C9, 0x17B8)),
        ("3.6", cps(0x1798, 0x17BB, 0x17D0), cps(0x1798, 0x17C9, 0x17D0)),
        ("3.6", cps(0x1798, 0x17BB, 0x17B6, 0x17C6), cps(0x1798, 0x17C9, 0x17B6, 0x17C6)),
        # BA makes a cluster weak even with a strong consonant before it (UTN #61 p. 22)
        (
            "3.6",
            cps(0x179F, 0x17D2, 0x1794, 0x17BB, 0x17B7),
            cps(0x179F, 0x17D2, 0x1794, 0x17C9, 0x17B7),
        ),
        # -u before a vowel that is not above-base stays -u
        ("3.6", cps(0x179F, 0x17BB, 0x17B6), cps(0x179F, 0x17BB, 0x17B6)),
        (
            "3.7",
            cps(0x179F, 0x17D2, 0x179A, 0x17D2, 0x1780),
            cps(0x179F, 0x17D2, 0x1780, 0x17D2, 0x179A),
        ),
        ("3.8", cps(0x1780, 0x17D2, 0x178A), cps(0x1780, 0x17D2, 0x178F)),
        # A base DA is not a coeng: only coeng da folds
        ("3.8", cps(0x178A, 0x17B6), cps(0x178A, 0x17B6)),
        # Rule 3.9: the -u left over after 3.6 is sorted and 3.5 applied again
        ("3.9", cps(0x1798, 0x17BB, 0x17BE, 0x17BB), cps(0x1798, 0x17C9, 0x17BB, 0x17BE)),
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
    assert oracle(nfc(text)) != text
    assert normalize(text) == text


@pytest.mark.parametrize(
    ("row", "source", "ours", "theirs"),
    [
        # O4: the shifter goes before the pre-base vowel; the oracle leaves it after,
        # and a second oracle pass moves it.
        (
            "O4",
            cps(0x179F, 0x17C1, 0x17BB, 0x17B7),
            cps(0x179F, 0x17CA, 0x17C1, 0x17B7),
            cps(0x179F, 0x17C1, 0x17CA, 0x17B7),
        ),
        # O4: with three coengs, coeng ro ends up last.
        (
            "O4",
            cps(0x1780, 0x17D2, 0x179A, 0x17D2, 0x1781, 0x17D2, 0x1782),
            cps(0x1780, 0x17D2, 0x1781, 0x17D2, 0x1782, 0x17D2, 0x179A),
            cps(0x1780, 0x17D2, 0x1781, 0x17D2, 0x179A, 0x17D2, 0x1782),
        ),
        # O5: NYO is weak (UTN #61 pp. 18, 23); the oracle's class has 1780 instead.
        (
            "O5",
            cps(0x1789, 0x17BB, 0x17B7),
            cps(0x1789, 0x17C9, 0x17B7),
            cps(0x1789, 0x17BB, 0x17B7),
        ),
        # O6: samyok sannya does not push triisap down (UTN #61 p. 25).
        (
            "O6",
            cps(0x179F, 0x17BB, 0x17D0),
            cps(0x179F, 0x17BB, 0x17D0),
            cps(0x179F, 0x17CA, 0x17D0),
        ),
        # O7: BA makes the cluster weak (UTN #61 prose, Q-008); SIL follows the regex.
        (
            "O7",
            cps(0x1794, 0x17D2, 0x1780, 0x17BB, 0x17B7),
            cps(0x1794, 0x17D2, 0x1780, 0x17C9, 0x17B7),
            cps(0x1794, 0x17D2, 0x1780, 0x17CA, 0x17B7),
        ),
        # O7: with three coengs the regex misses the strong base; the prose does not.
        (
            "O7",
            cps(0x1780, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17BB, 0x17B7),
            cps(0x1780, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17CA, 0x17B7),
            cps(0x1780, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17C9, 0x17B7),
        ),
        # O8: a second robat is outside the cluster grammar; the oracle still matches
        # the coeng alone.
        (
            "O8",
            cps(0x179F, 0x17CC, 0x17CC, 0x17D2, 0x179A, 0x17BB, 0x17B9),
            cps(0x179F, 0x17CC, 0x17CC, 0x17D2, 0x179A, 0x17BB, 0x17B9),
            cps(0x179F, 0x17CC, 0x17CC, 0x17D2, 0x179A, 0x17C9, 0x17B9),
        ),
    ],
)
def test_documented_oracle_difference(row, source, ours, theirs):
    assert oracle(source) == theirs
    assert normalize(source) == ours


def test_preserve_coeng_da():
    text = cps(0x1780, 0x17D2, 0x178A, 0x17B6)
    assert normalize(text) == cps(0x1780, 0x17D2, 0x178F, 0x17B6)
    assert normalize(text, preserve_coeng_da=True) == text


def test_public_api():
    assert pheasa.normalize is normalize
    assert pheasa.NORMALIZATION_VERSION == "1"


# --- Properties -----------------------------------------------------------------------


@settings(max_examples=1000)
@given(wellformed_text)
def test_matches_oracle_on_wellformed_clusters(text):
    assert_matches_oracle(text)


@settings(max_examples=2000)
@given(khmer_text)
def test_matches_oracle_on_any_khmer_text(text):
    assert_matches_oracle(text)


@settings(max_examples=2000)
@given(st.lists(u_cluster, min_size=1, max_size=3).map(" ".join))
def test_matches_oracle_on_u_clusters(text):
    # Rule 3.6 is the only fold with context, so it gets its own generator.
    assert_matches_oracle(text)


@settings(max_examples=1000)
@given(st.lists(u_cluster, min_size=1, max_size=3).map(" ".join))
def test_u_clusters_without_documented_differences_match_exactly(text):
    if not u_deviation_possible(text):
        ours, theirs = normalize(text), oracle(text)
        assert ours == theirs or oracle(theirs) != theirs


@settings(max_examples=1000)
@given(st.one_of(mixed_text, wellformed_text, u_cluster))
def test_idempotent(text):
    # Requirement 2
    once = normalize(text)
    assert normalize(once) == once


@settings(max_examples=1000)
@given(st.one_of(mixed_text, wellformed_text, u_cluster))
def test_nfc_invariant(text):
    # Requirement 3
    once = normalize(text)
    assert nfc(once) == once


@settings(max_examples=1000)
@given(khmer_text)
def test_no_lost_bases(text):
    # Requirement 4. After Stage 1 (NFC; this alphabet has no BOM), cluster-starting
    # bases keep their order, and no fold other than 3.8 (coeng da) touches a base.
    cleaned = nfc(text)
    assert cluster_bases(normalize(text)) == cluster_bases(cleaned)
    kept = normalize(text, preserve_coeng_da=True)
    assert Counter(c for c in kept if c in BASE_SET) == Counter(c for c in cleaned if c in BASE_SET)


@given(
    st.sampled_from(BASES),
    st.lists(st.sampled_from(sorted(TOKENS_BY_KEY)), unique=True).flatmap(
        lambda keys: st.tuples(*(TOKENS_BY_KEY[k] for k in keys))
    ),
    st.randoms(use_true_random=False),
)
def test_typing_order_of_distinct_keys_does_not_matter(base, tokens, rnd):
    # Requirement 5, for Stages 2 and 3: tokens with different sort keys can be typed in
    # any order. (Whether two orders render alike is a separate, human question.)
    shuffled = list(tokens)
    rnd.shuffle(shuffled)
    assert normalize(base + "".join(shuffled)) == normalize(base + "".join(tokens))
