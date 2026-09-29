"""Validation: flag text that does not fit the Modern Khmer syllable structure.

Implements the "Validation" section of `spec/normalization.md`. Issue codes (V1-V9)
are defined there. Validation never modifies text.
"""

import re
from dataclasses import dataclass

from pheasa.normalize import (
    _ABOVE_VOWELS,
    _BASE_CLASS,
    _KEYS,
    BOM,
    COENG,
    MUUSIKATOAN,
    SAMYOK_SANNYA,
    TRIISAP,
    ZWJ,
    ZWNJ,
    Key,
    _is_strong,
)

__all__ = ["Issue", "validate"]


@dataclass(frozen=True)
class Issue:
    """Something in the text that normalization could not safely fix.

    `start` and `end` are offsets into the validated text.
    """

    code: str
    start: int
    end: int
    message: str


# Source: UTN #61 p. 16 (Modern Khmer syllable). The shifter's ZWNJ context is checked
# in code below. U+17D3 is accepted as a modifier, as in Stage 2 and SIL (spec C3), and
# flagged separately (V7).
_NON_RO = "[\u1780-\u1799\u179b-\u17a2\u17a5-\u17b3]"
# U+25CC DOTTED CIRCLE may stand in for a base or a coeng's base, as in SIL khtest's `B`
# pattern, so that a mark shown on its own (dictionaries, teaching) is not flagged.
DOTTED_CIRCLE = "\u25cc"
_ANY_BASE = f"(?:{_BASE_CLASS}|{DOTTED_CIRCLE})"
_SYLLABLE = re.compile(
    # Base Robat? Coengs?
    f"({_ANY_BASE}\u17cc?(?:(?:\u17d2{_NON_RO})?\u17d2{_ANY_BASE})?)"
    "([\u17c9\u17ca]\u200c?)?"  # Shifter (with its optional ZWNJ)
    "[\u17b6-\u17c5]?"  # Vowel
    "(?:(?:[\u17c6\u17cb\u17cd-\u17cf\u17d1\u17d3]|(?<!\u17bb)[\u17d0\u17dd])"  # Modifiers
    "[\u17c6\u17cb\u17cd-\u17d1\u17d3\u17dd]?)?"
    "[\u17c7\u17c8]?"  # Final
)
# Source: UTN #61 p. 35; D-009 (flagged, not converted)
_LUNAR = re.compile("[\u17e0-\u17e9]\u17d2\u17d4|\u17d4\u17d2[\u17e0-\u17e9\u17d4]")
# Marks that must belong to a syllable. U+17D3 is Other in UTN #61 (p. 16), so it may
# stand alone; ZWNJ and ZWJ are handled separately.
_MARKS = frozenset(ch for ch, key in _KEYS.items() if Key.ROBAT <= key <= Key.FINAL) - {
    ZWNJ,
    "\u17d3",
}
_KHMER_SIGNS = frozenset(chr(cp) for cp in range(0x1780, 0x17DE))
U = "\u17bb"


def _zwnj_allowed(cluster: str, shifter: str, after: str) -> bool:
    """UTN #61 p. 16: ZWNJ only where the shifter would otherwise downshift."""
    above = after[:1] in _ABOVE_VOWELS or after[:2] == "\u17b6\u17c6"
    if _is_strong(cluster):
        return shifter == TRIISAP and above
    samyok = after[:1] == SAMYOK_SANNYA or (
        after[:1] in "\u17c1\u17c2\u17c3" and after[1:2] == SAMYOK_SANNYA
    )
    return shifter == MUUSIKATOAN and (above or samyok)


def _mark_issue(text: str, i: int, after_syllable: bool) -> Issue:
    ch = text[i]
    name = f"U+{ord(ch):04X}"
    if ch == COENG:
        if i + 1 < len(text) and (
            _KEYS.get(text[i + 1]) is Key.BASE or text[i + 1] == DOTTED_CIRCLE
        ):
            return Issue("V4", i, i + 2, "coeng beyond the two allowed, or coeng ro first")
        return Issue("V1", i, i + 1, "coeng is not followed by a base")
    if not after_syllable:
        return Issue("V5", i, i + 1, f"{name} has no base before it")
    if text[i - 1] == U and (ch in _ABOVE_VOWELS or ch == SAMYOK_SANNYA):
        return Issue("V4", i, i + 1, f"{name} after -u: a consonant shifter may be meant")
    return Issue("V4", i, i + 1, f"{name} does not fit the syllable structure")


def validate(text: str, *, start_of_text: bool = True) -> tuple[Issue, ...]:
    """Return the issues found in `text`, in order. The text is not changed.

    Pass `start_of_text=False` when `text` continues earlier text (for example, a later
    line of a file), so that a U+FEFF at its start is flagged as mid-text (V8).
    """
    issues: list[Issue] = []
    n = len(text)
    i = 0
    after_syllable = False  # the previous character belongs to a syllable
    while i < n:
        ch = text[i]
        lunar = _LUNAR.match(text, i)
        if lunar:
            issues.append(Issue("V6", i, lunar.end(), "legacy lunar-date sequence"))
            i, after_syllable = lunar.end(), False
            continue
        if _KEYS.get(ch) is Key.BASE or ch == DOTTED_CIRCLE:
            m = _SYLLABLE.match(text, i)
            cluster, shifter = m.group(1), m.group(2)
            after = text[m.end(2) : m.end(2) + 2] if shifter else ""
            if shifter and shifter.endswith(ZWNJ) and not _zwnj_allowed(cluster, shifter[0], after):
                at = m.end(2) - 1
                issues.append(Issue("V2", at, at + 1, "ZWNJ where the shifter would not downshift"))
            i, after_syllable = m.end(), True
            continue
        if ch in _MARKS:
            issue = _mark_issue(text, i, after_syllable)
            issues.append(issue)
            i = issue.end
            continue
        if ch in (ZWNJ, ZWJ):
            near_khmer = (i > 0 and text[i - 1] in _KHMER_SIGNS) or (
                i + 1 < n and text[i + 1] in _MARKS
            )
            if (
                ch == ZWJ
                and text[i + 1 : i + 2] == COENG
                and _KEYS.get(text[i + 2 : i + 3]) is Key.BASE
            ):
                issues.append(Issue("V3", i, i + 3, "final coeng (Middle Khmer only)"))
                i += 3
                continue
            if near_khmer:
                name = "ZWNJ" if ch == ZWNJ else "ZWJ"
                issues.append(
                    Issue(
                        "V2" if ch == ZWNJ else "V3",
                        i,
                        i + 1,
                        f"{name} outside a permitted position",
                    )
                )
        elif ch == BOM and (i > 0 or not start_of_text):
            issues.append(Issue("V8", i, i + 1, "U+FEFF inside the text (rule 1.2)"))
        i += 1
        after_syllable = False
    # Spec conflict C3: U+17D3 is discouraged, Identifier_Type=Obsolete (UTN #61 p. 27)
    issues.extend(
        Issue("V7", k, k + 1, "U+17D3 is discouraged") for k, c in enumerate(text) if c == "\u17d3"
    )
    return tuple(sorted(issues, key=lambda issue: (issue.start, issue.code)))
