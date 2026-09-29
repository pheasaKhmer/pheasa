"""The change report behind `normalize(text, report=True)` (spec "Validation").

The input is tracked as a list of pieces, each covering a span of the input. Every
stage edits the pieces it touches and records the rule that did it, so each change in
the report points back to the exact input characters it came from.
"""

import unicodedata
from dataclasses import dataclass, field

from pheasa.normalize import (
    _DEPRECATED_TABLE,
    _DIGIT_TABLES,
    _ZWSP_TABLES,
    BOM,
    _clusters,
    _is_stable,
    _normalize_cluster,
    _option_table,
)
from pheasa.validate import Issue, validate

__all__ = ["Change", "Report"]


@dataclass(frozen=True)
class Change:
    """One edit: input[start:end] (`before`) became `after`, by the listed rules.

    `output_start` is where `after` begins in the normalized text.
    """

    rules: tuple[str, ...]
    start: int
    end: int
    before: str
    after: str
    output_start: int


@dataclass(frozen=True)
class Report:
    """The normalized text, every change made to reach it, and the issues left in it."""

    text: str
    changes: tuple[Change, ...]
    issues: tuple[Issue, ...]


@dataclass
class _Piece:
    start: int
    end: int
    text: str
    rules: list[str] = field(default_factory=list)


def _add_rules(target: list[str], rules: list[str]) -> None:
    target.extend(rule for rule in rules if rule not in target)


def _apply(pieces: list[_Piece], edits: list[tuple[int, int, str, list[str]]]) -> list[_Piece]:
    """Apply non-overlapping edits (start, end, new text, rules) to the joined text.

    Offsets are into the current joined text. Pieces an edit touches are merged, so a
    change is always reported against whole input spans.
    """
    if not edits:
        return pieces
    owner = [k for k, piece in enumerate(pieces) for _ in piece.text]
    groups: list[list] = []  # [first piece, last piece, [edits]]
    for edit in sorted(edits):
        first, last = owner[edit[0]], owner[edit[1] - 1]
        if groups and first <= groups[-1][1]:
            groups[-1][1] = max(groups[-1][1], last)
            groups[-1][2].append(edit)
        else:
            groups.append([first, last, [edit]])
    joined = _joined(pieces)
    offsets = [0]
    for piece in pieces:
        offsets.append(offsets[-1] + len(piece.text))
    out: list[_Piece] = []
    done = 0
    for first, last, group_edits in groups:
        out += pieces[done:first]
        merged = _Piece(pieces[first].start, pieces[last].end, "")
        position = offsets[first]
        parts = []
        for piece in pieces[first : last + 1]:
            _add_rules(merged.rules, piece.rules)
        for start, end, new, rules in group_edits:
            parts += (joined[position:start], new)
            position = end
            _add_rules(merged.rules, rules)
        parts.append(joined[position : offsets[last + 1]])
        merged.text = "".join(parts)
        out.append(merged)
        done = last + 1
    out += pieces[done:]
    return out


def _joined(pieces: list[_Piece]) -> str:
    return "".join(piece.text for piece in pieces)


def _starts_segment(chunk: str, ch: str) -> bool:
    """Can NFC treat `chunk` and everything from `ch` on independently? (UAX #15)

    `ch` must decompose to a starter, so that later marks attach to it rather than to
    `chunk`, and it must not compose with the end of `chunk`.
    """
    nfd = unicodedata.normalize("NFD", ch)
    if unicodedata.combining(nfd[0]):
        return False
    nfc = unicodedata.normalize
    return nfc("NFC", chunk + ch) == nfc("NFC", chunk) + nfc("NFC", ch)


def _nfc_edits(text: str) -> list[tuple[int, int, str, list[str]]]:
    """Rule 1.3 as edits: split the text where NFC cannot act across, then NFC each part."""
    if unicodedata.is_normalized("NFC", text):
        return []
    edits = []
    start = 0
    for i in range(1, len(text) + 1):
        if i < len(text) and not _starts_segment(text[start:i], text[i]):
            continue
        chunk = text[start:i]
        normalized = unicodedata.normalize("NFC", chunk)
        if normalized != chunk:
            edits.append((start, i, normalized, ["1.3"]))
        start = i
    return edits


def build_report(
    text: str,
    *,
    preserve_coeng_da: bool,
    zwsp: str,
    digits: str,
    fold_deprecated: bool,
) -> Report:
    _option_table(zwsp, digits, fold_deprecated)  # validates the option values
    pieces = [_Piece(i, i + 1, ch) for i, ch in enumerate(text)]

    # Rule 1.1
    leading = len(text) - len(text.lstrip(BOM))
    for piece in pieces[:leading]:
        piece.text, piece.rules = "", ["1.1"]

    # Stage 4, one table per option so that each change names its option
    tables = [
        ("4.zwsp", _ZWSP_TABLES[zwsp]),
        ("4.digits", _DIGIT_TABLES[digits]),
        ("4.deprecated", _DEPRECATED_TABLE if fold_deprecated else {}),
    ]
    for piece in pieces[leading:]:
        for rule, table in tables:
            if ord(piece.text) in table:
                piece.text, piece.rules = table[ord(piece.text)] or "", [rule]
                break

    # Rule 1.3
    pieces = _apply(pieces, _nfc_edits(_joined(pieces)))

    # Stages 2 and 3, with rule 2.3
    joined = _joined(pieces)
    edits = []
    for i, j in _clusters(joined):
        cluster, fired = joined[i:j], []
        result = _normalize_cluster(cluster, preserve_coeng_da=preserve_coeng_da, fired=fired)
        if result != cluster and (j == len(joined) or _is_stable(result, joined[j])):
            edits.append((i, j, result, fired))
    pieces = _apply(pieces, edits)

    output = _joined(pieces)
    changes = []
    position = 0
    for piece in pieces:
        before = text[piece.start : piece.end]
        if piece.text != before:
            changes.append(
                Change(tuple(piece.rules), piece.start, piece.end, before, piece.text, position)
            )
        position += len(piece.text)

    issues = list(validate(output))
    # Rule 2.3: clusters that are left as typed because normalizing them is unsafe
    for i, j in _clusters(output):
        cluster = output[i:j]
        if _normalize_cluster(cluster, preserve_coeng_da=preserve_coeng_da) != cluster:
            issues.append(Issue("V9", i, j, "cluster left as typed (rule 2.3)"))
    issues.sort(key=lambda issue: (issue.start, issue.code))
    return Report(output, tuple(changes), tuple(issues))
