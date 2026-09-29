"""Khmer text normalization.

Implements `spec/normalization.md`. Rule numbers in comments refer to that document.
Stages implemented: 1 (pre-clean), 2 (cluster reordering), 3 (folds) and 4 (options).
"""

import re
import unicodedata
from collections.abc import Iterator
from enum import IntEnum
from typing import TYPE_CHECKING, Literal, overload

if TYPE_CHECKING:
    from pheasa.report import Report

__all__ = ["NORMALIZATION_VERSION", "DigitsOption", "ZwspOption", "normalize"]

ZwspOption = Literal["keep", "strip", "space"]
DigitsOption = Literal["keep", "khmer", "ascii"]

# Names the rule set in spec/normalization.md. Any change to the output for any input
# needs a new version, a CHANGELOG entry and a DECISIONS entry (D-013).
NORMALIZATION_VERSION = "1"

BOM = "\ufeff"
COENG = "\u17d2"
ZWNJ = "\u200c"
ZWJ = "\u200d"
ZWSP = "\u200b"


class Key(IntEnum):
    """Sort key of a character inside a syllable cluster (spec Stage 2 table)."""

    OTHER = 0  # ends a cluster, never moved
    BASE = 1
    ROBAT = 2
    COENG = 3  # COENG and the base it subjoins
    SHIFTER = 4
    ZWNJ = 5
    VOWEL_PRE = 6
    VOWEL_BELOW = 7
    VOWEL_ABOVE = 8
    VOWEL_POST = 9
    MODIFIER = 10
    FINAL = 11
    FINAL_COENG = 12  # ZWJ, and every COENG or base chained after it


_KEY_RANGES = (
    # Source: UTN #61 p. 16 (consonants are bases)
    (0x1780, 0x17A2, Key.BASE),
    # Source: UTN #61 p. 13; TUS 18.0 §16.4 (deprecated independent vowels are Other)
    (0x17A3, 0x17A4, Key.OTHER),
    # Source: UTN #61 p. 16 (independent vowels are bases)
    (0x17A5, 0x17B3, Key.BASE),
    # Source: UTN #61 p. 13 (inherent vowels 17B4, 17B5 are Other)
    (0x17B4, 0x17B5, Key.OTHER),
    # Source: UTN #61 p. 16 (vowel slot); SIL khnormal categories (vowel sub-order)
    (0x17B6, 0x17B6, Key.VOWEL_POST),
    (0x17B7, 0x17BA, Key.VOWEL_ABOVE),
    (0x17BB, 0x17BD, Key.VOWEL_BELOW),
    (0x17BE, 0x17C5, Key.VOWEL_PRE),
    # Source: UTN #61 p. 16 (modifier and final slots)
    (0x17C6, 0x17C6, Key.MODIFIER),
    (0x17C7, 0x17C8, Key.FINAL),
    # Source: UTN #61 pp. 16, 25 (shifters follow the coengs; spec conflict C1)
    (0x17C9, 0x17CA, Key.SHIFTER),
    (0x17CB, 0x17CB, Key.MODIFIER),
    # Source: UTN #61 p. 16 (robat directly follows the base)
    (0x17CC, 0x17CC, Key.ROBAT),
    (0x17CD, 0x17D1, Key.MODIFIER),
    # Source: UTN #61 p. 16
    (0x17D2, 0x17D2, Key.COENG),
    # Source: SIL khnormal categories; UTN #61 pp. 13, 16 say Other (spec conflict C3)
    (0x17D3, 0x17D3, Key.MODIFIER),
    # Source: UTN #61 p. 13 (punctuation and currency signs are Other)
    (0x17D4, 0x17DC, Key.OTHER),
    # Source: UTN #61 p. 16
    (0x17DD, 0x17DD, Key.MODIFIER),
    # Source: UTN #61 p. 16 (ZWNJ after a shifter)
    (0x200C, 0x200C, Key.ZWNJ),
    # Source: UTN #61 pp. 14-15 (ZWJ marks a final coeng)
    (0x200D, 0x200D, Key.FINAL_COENG),
)

_KEYS: dict[str, Key] = {
    chr(cp): key for first, last, key in _KEY_RANGES for cp in range(first, last + 1)
}

# A base or COENG right after one of these belongs to the unit the joiner opened
# (a subscript, or a Middle Khmer final coeng) and takes the joiner's sort key.
# Source: UTN #61 p. 16 (coeng + base is one unit); pp. 14-15 (ZWJ + coeng)
_JOINERS = frozenset({COENG, ZWJ})

# Canonical combining classes of the Khmer characters that have one.
# Source: UCD 18.0.0 UnicodeData.txt (all other Khmer characters are ccc=0)
_KHMER_CCC = {COENG: 9, "\u17dd": 230}


def _ccc(ch: str) -> int:
    if ch in _KHMER_CCC:
        return _KHMER_CCC[ch]
    return unicodedata.combining(ch)


# --- Stage 4 tables (applied during pre-clean, before NFC; see spec "Pipeline") --------

_ZWSP_TABLES = {"keep": {}, "strip": {ord(ZWSP): None}, "space": {ord(ZWSP): " "}}
# Source: UCD 18.0.0 (17E0-17E9 are gc=Nd with decimal values 0-9). 17F0-17F9 are
# gc=No divination numerals and are never converted.
_DIGIT_TABLES = {
    "keep": {},
    "khmer": {0x30 + d: chr(0x17E0 + d) for d in range(10)},
    "ascii": {0x17E0 + d: chr(0x30 + d) for d in range(10)},
}
# Source: UTN #61 pp. 27, 30 (intentional confusables); TUS 18.0 §16.4 (deprecated and
# discouraged characters). 17B4 and 17B5 are Default_Ignorable (UTN #61 p. 27).
_DEPRECATED_TABLE = {
    0x17A3: "\u17a2",
    0x17A4: "\u17a2\u17b6",
    0x17D8: "\u17d4\u179b\u17d4",
    0x17B4: None,
    0x17B5: None,
}


def _option_table(zwsp: str, digits: str, fold_deprecated: bool) -> dict[int, str | None]:
    if zwsp not in _ZWSP_TABLES:
        raise ValueError(f"zwsp must be one of {sorted(_ZWSP_TABLES)}, not {zwsp!r}")
    if digits not in _DIGIT_TABLES:
        raise ValueError(f"digits must be one of {sorted(_DIGIT_TABLES)}, not {digits!r}")
    table = {**_ZWSP_TABLES[zwsp], **_DIGIT_TABLES[digits]}
    if fold_deprecated:
        table.update(_DEPRECATED_TABLE)
    return table


def _pre_clean(text: str, table: dict[int, str | None], *, start_of_text: bool = True) -> str:
    # Rule 1.1: a leading byte order mark (or a run of them) is not text.
    # Source: TUS 18.0 §23.8
    if start_of_text:
        text = text.lstrip(BOM)
    # Stage 4 runs here so that its output is normalized like any other text.
    text = text.translate(table)
    # Rule 1.3. Source: UAX #15
    return unicodedata.normalize("NFC", text)


def _is_stable(ordered: str, following: str) -> bool:
    """Rule 2.3: can the sorted cluster be emitted without changing its neighbour?"""
    last = ordered[-1]
    # A trailing COENG or ZWJ would pull the next syllable's base into this cluster, so
    # normalizing the output again would give a different result.
    if last in _JOINERS and _KEYS.get(following) is Key.BASE:
        return False
    # NFC would reorder the cluster's last mark with the next character.
    ccc_next = _ccc(following)
    return not 0 < ccc_next < _ccc(last)


# --- Stage 3 -------------------------------------------------------------------------

# Rule 3.1. Source: SIL khnormal (repeated invisible characters after a coeng)
_REPEATED_AFTER_COENG = re.compile("(\u200d?\u17d2)[\u17d2\u200c\u200d]+")
# Rules 3.3 and 3.4. Source: UTN #61 p. 28 ("Do not use" table, split vowels)
_E_THEN_II = re.compile("\u17c1([\u17bb-\u17bd]?)\u17b8")
_E_THEN_AA = re.compile("\u17c1([\u17bb-\u17bd]?)\u17b6")
# Rule 3.7. Source: UTN #61 pp. 16, 29 (coeng ro is second of two coengs)
_COENG_RO_FIRST = re.compile("(\u17d2\u179a)(\u17d2[\u1780-\u17a2\u17a5-\u17b3])")

# Rule 3.6: the consonant cluster (UTN #61 p. 16: Base Robat? Coengs), then an optional
# pre-base vowel, then -u. UTN #61 p. 18 (Middle Khmer AboveVowel) allows 17C1-17C5
# before the above vowel; the Stage 2 sort puts that vowel before the -u.
_BASE_CLASS = "[\u1780-\u17a2\u17a5-\u17b3]"
_U_AFTER_CLUSTER = re.compile(
    f"({_BASE_CLASS}\u17cc?(?:\u17d2{_BASE_CLASS})*)([\u17c1-\u17c5]?)\u17bb"
)
# Source: UTN #61 p. 16 (StrongBase), p. 23 (S1 = StrongBase)
_STRONG_BASES = frozenset(
    chr(cp)
    for first, last in (
        (0x1780, 0x1783),
        (0x1785, 0x1788),
        (0x178A, 0x178D),
        (0x178F, 0x1792),
        (0x1795, 0x1797),
        (0x179E, 0x17A0),
        (0x17A2, 0x17A2),
    )
    for cp in range(first, last + 1)
)
BA = "\u1794"


def _is_strong(cluster: str) -> bool:
    """Is a consonant cluster (base, robat, coengs) STRONG?

    UTN #61 p. 17 and p. 22 (rules 1-3): strong means it contains a series 1 consonant
    and no BA. The p. 16 regex, used as a lookbehind, can disagree after a BA or with 3+
    coengs; the prose wins (spec C4, Q-008, D-012). Independent vowels are weak (p. 24).
    """
    consonants = cluster.replace("\u17cc", "").replace(COENG, "")
    return BA not in consonants and any(c in _STRONG_BASES for c in consonants)


# Source: UTN #61 p. 16 (AboveVowel); 17B6 counts only with a following 17C6
_ABOVE_VOWELS = frozenset("\u17b7\u17b8\u17b9\u17ba\u17be\u17dd")
MUUSIKATOAN = "\u17c9"
TRIISAP = "\u17ca"
SAMYOK_SANNYA = "\u17d0"


def _shifter_for_u(cluster: str, pre: str, after: str) -> str | None:
    """Rule 3.6: the shifter a -u stands for, or None to leave the -u alone."""
    above = after[:1] in _ABOVE_VOWELS or after[:2] == "\u17b6\u17c6"
    if _is_strong(cluster):
        # UTN #61 p. 25: samyok sannya does not push triisap down (spec O6).
        return TRIISAP if above else None
    # UTN #61 p. 16: AboveVowelSamyok = AboveVowel | [17C1-17C3]? 17D0
    samyok = after[:1] == SAMYOK_SANNYA and pre in ("", "\u17c1", "\u17c2", "\u17c3")
    return MUUSIKATOAN if above or samyok else None


def _u_to_shifter(text: str) -> str:
    match = _U_AFTER_CLUSTER.match(text)
    if match is None:
        return text
    cluster, pre = match.groups()
    shifter = _shifter_for_u(cluster, pre, text[match.end() :])
    if shifter is None:
        return text
    # The shifter goes in its Stage 2 position, before any pre-base vowel.
    return cluster + shifter + pre + text[match.end() :]


def _fold(text: str, *, preserve_coeng_da: bool, fired: list[str] | None = None) -> str:
    """Stage 3: replace "do not use" sequences in a sorted cluster, in spec order.

    If `fired` is given, the ID of every rule that changed the text is appended to it.
    """

    def step(rule: str, new: str) -> str:
        if fired is not None and new != text:
            fired.append(rule)
        return new

    text = step("3.1", _REPEATED_AFTER_COENG.sub(r"\1", text))
    # Source: UTN #61 p. 29 (visually indistinct)
    text = step("3.2", text.replace("\u17be\u17b6", "\u17c4\u17b8"))
    text = step("3.3", _E_THEN_II.sub("\u17be\\1", text))
    text = step("3.4", _E_THEN_AA.sub("\u17c4\\1", text))
    # Source: SIL khnormal; UTN #61 pp. 28, 30 (<17BE 17BB> stands for shifter + 17BE)
    text = step("3.5", text.replace("\u17be\u17bb", "\u17bb\u17be"))
    text = step("3.6", _u_to_shifter(text))
    # 3.7, repeated so that a third coeng cannot leave coeng ro in front (spec O4).
    while (swapped := _COENG_RO_FIRST.sub(r"\2\1", text)) != text:
        text = step("3.7", swapped)
    if not preserve_coeng_da:
        # Source: UTN #61 pp. 31-32; D-008
        text = step("3.8", text.replace(COENG + "\u178a", COENG + "\u178f"))
    return text


def _key_at(text: str, j: int, previous: Key) -> Key:
    """Sort key of text[j] inside a cluster, given the key of text[j - 1]."""
    key = _KEYS.get(text[j], Key.OTHER)
    if key in (Key.BASE, Key.COENG) and text[j - 1] in _JOINERS:
        return previous
    return key


def _sort(cluster: str) -> str:
    """Rule 2.2: sorted() is stable, so typed order is kept within a key."""
    keys = [Key.BASE]
    for j in range(1, len(cluster)):
        keys.append(_key_at(cluster, j, keys[-1]))
    return "".join(cluster[k] for k in sorted(range(len(cluster)), key=keys.__getitem__))


def _normalize_cluster(
    cluster: str, *, preserve_coeng_da: bool, fired: list[str] | None = None
) -> str:
    """Stages 2 and 3 on one cluster, repeated until the result no longer changes.

    A fold can leave the cluster unsorted or expose another fold (rule 3.9). Each round
    either shortens the cluster, removes a -u, 17BE or coeng da, or only permutes it, and
    a round after a permutation-only round changes nothing, so the loop ends.
    """
    rounds = 0
    while True:
        ordered = _sort(cluster)
        if fired is not None and ordered != cluster:
            fired.append("2.2")
        result = _fold(ordered, preserve_coeng_da=preserve_coeng_da, fired=fired)
        if result == cluster:
            return cluster
        rounds += 1
        if fired is not None and rounds == 2:
            fired.append("3.9")
        cluster = result


def _clusters(text: str) -> Iterator[tuple[int, int]]:
    """Yield the (start, end) span of every syllable cluster in `text` (rule 2.1)."""
    n = len(text)
    i = 0
    while i < n:
        # A cluster starts at a base that is not part of a joiner unit.
        if _KEYS.get(text[i]) is not Key.BASE or (i > 0 and text[i - 1] in _JOINERS):
            i += 1
            continue
        key = Key.BASE
        j = i + 1
        while j < n and (key := _key_at(text, j, key)) > Key.BASE:
            j += 1
        yield i, j
        i = j


def _reorder(text: str, *, preserve_coeng_da: bool = False) -> str:
    """Stages 2 and 3: normalize each syllable cluster in turn."""
    out: list[str] = []
    done = 0
    # Syllables repeat a lot in real text, so remember each cluster's result for this call.
    memo: dict[str, str] = {}
    for i, j in _clusters(text):
        if j - i <= 2:
            continue  # a base plus one mark is always already in order and has no fold
        cluster = text[i:j]
        result = memo.get(cluster)
        if result is None:
            result = memo[cluster] = _normalize_cluster(
                cluster, preserve_coeng_da=preserve_coeng_da
            )
        # Rule 2.3: keep the cluster as typed if the result would disturb its neighbour.
        if result != cluster and (j == len(text) or _is_stable(result, text[j])):
            out += (text[done:i], result)
            done = j
    out.append(text[done:])
    return "".join(out)


@overload
def normalize(
    text: str,
    *,
    report: Literal[False] = False,
    preserve_coeng_da: bool = False,
    zwsp: ZwspOption = "keep",
    digits: DigitsOption = "keep",
    fold_deprecated: bool = False,
) -> str: ...


@overload
def normalize(
    text: str,
    *,
    report: Literal[True],
    preserve_coeng_da: bool = False,
    zwsp: ZwspOption = "keep",
    digits: DigitsOption = "keep",
    fold_deprecated: bool = False,
) -> "Report": ...


def normalize(
    text: str,
    *,
    report: bool = False,
    preserve_coeng_da: bool = False,
    zwsp: ZwspOption = "keep",
    digits: DigitsOption = "keep",
    fold_deprecated: bool = False,
) -> "str | Report":
    """Return the normalized form of `text` (spec/normalization.md).

    With `report=True`, return a `pheasa.Report` instead: the normalized text, every
    change made (with input offsets and rule IDs) and the validation issues left in it.

    Options (all off by default, spec Stage 4):

    - `preserve_coeng_da=True` turns off rule 3.8 (coeng da is stored as coeng ta).
    - `zwsp`: `"keep"`, `"strip"` or `"space"` for U+200B ZERO WIDTH SPACE.
    - `digits`: `"keep"`, `"khmer"` (0-9 to U+17E0-17E9) or `"ascii"` (the reverse).
    - `fold_deprecated=True` replaces deprecated and discouraged Khmer characters.
    """
    if report:
        from pheasa.report import build_report  # imports this module

        return build_report(
            text,
            preserve_coeng_da=preserve_coeng_da,
            zwsp=zwsp,
            digits=digits,
            fold_deprecated=fold_deprecated,
        )
    return _normalize(
        text,
        preserve_coeng_da=preserve_coeng_da,
        zwsp=zwsp,
        digits=digits,
        fold_deprecated=fold_deprecated,
    )


def _normalize(
    text: str,
    *,
    preserve_coeng_da: bool = False,
    zwsp: str = "keep",
    digits: str = "keep",
    fold_deprecated: bool = False,
    start_of_text: bool = True,
) -> str:
    """`normalize` without the report. `start_of_text=False` is for text that continues
    earlier text, such as a later line of a file: rule 1.1 then does not apply."""
    table = _option_table(zwsp, digits, fold_deprecated)
    text = _pre_clean(text, table, start_of_text=start_of_text)
    return _reorder(text, preserve_coeng_da=preserve_coeng_da)
