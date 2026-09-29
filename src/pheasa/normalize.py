"""Khmer text normalization.

Implements `spec/normalization.md`. Rule numbers in comments refer to that document.
Stages implemented so far: 1 (pre-clean) and 2 (cluster reordering).
"""

import unicodedata
from enum import IntEnum

__all__ = ["NORMALIZATION_VERSION", "normalize"]

# "0" means the spec is only partly implemented and output may still change. It becomes
# "1" once every stage of spec/normalization.md is in place.
NORMALIZATION_VERSION = "0"

BOM = "\ufeff"
COENG = "\u17d2"
ZWNJ = "\u200c"
ZWJ = "\u200d"


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


def _pre_clean(text: str) -> str:
    # Rule 1.1: a leading byte order mark (or a run of them) is not text.
    # Source: TUS 18.0 §23.8
    text = text.lstrip(BOM)
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


def _reorder(text: str) -> str:
    """Stage 2: stably sort each syllable cluster by sort key."""
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        # Rule 2.1: a cluster starts at a base that is not part of a joiner unit.
        if _KEYS.get(ch) is not Key.BASE or (i > 0 and text[i - 1] in _JOINERS):
            out.append(ch)
            i += 1
            continue
        keys = [Key.BASE]
        j = i + 1
        while j < n:
            key = _KEYS.get(text[j], Key.OTHER)
            if key in (Key.BASE, Key.COENG) and text[j - 1] in _JOINERS:
                key = keys[-1]
            if key <= Key.BASE:
                break
            keys.append(key)
            j += 1
        cluster = text[i:j]
        # Rule 2.2: sorted() is stable, so typed order is kept within a key.
        ordered = "".join(cluster[k] for k in sorted(range(len(cluster)), key=keys.__getitem__))
        if ordered != cluster and (j == n or _is_stable(ordered, text[j])):
            out.append(ordered)
        else:
            out.append(cluster)
        i = j
    return "".join(out)


def normalize(text: str) -> str:
    """Return the normalized form of `text` (spec/normalization.md)."""
    return _reorder(_pre_clean(text))
