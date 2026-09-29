"""Deterministic scoring for benchmark tasks.

Every metric compares text after `pheasa.normalize`, so a model is never penalized for
typing a correct answer in a different but equivalent encoding.
"""

from __future__ import annotations

import re
from collections import Counter

from pheasa.normalize import normalize

__all__ = ["boundary_f1", "canonical", "choice", "chrf", "corpus_chrf", "exact"]

_PUNCTUATION = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_SEPARATORS = re.compile("[ \u200b]+")


def canonical(text: str) -> str:
    """Normalize, drop ZWSP, collapse whitespace and casefold (Latin answers)."""
    text = normalize(text, zwsp="strip")
    return " ".join(text.split()).casefold()


def exact(prediction: str, reference: str) -> float:
    return float(canonical(prediction) == canonical(reference))


_ANSWER = re.compile(r"(?i)answer\s*[:\uff1a]\s*\(?([A-Z])\)?")
_LETTER = re.compile(r"\b([A-Z])\b")


def choice(prediction: str, reference: str) -> float:
    """Multiple choice: the letter after 'Answer:', else the first standalone capital."""
    match = _ANSWER.search(prediction) or _LETTER.search(prediction)
    return float(bool(match) and match.group(1).upper() == reference.strip().upper())


# --- chrF++ ---------------------------------------------------------------------------
# Popovic (2015, 2017): character n-grams up to 6 and word n-grams up to 2, F-beta with
# beta = 2. Implemented to match sacreBLEU 2.x (whitespace ignored for character
# n-grams, one punctuation mark split from each word, precision and recall averaged
# over the orders that occur); tests compare against sacreBLEU.


def _words(text: str) -> list[str]:
    words: list[str] = []
    for word in text.split():
        if len(word) > 1 and word[-1] in _PUNCTUATION:
            words += [word[:-1], word[-1]]
        elif len(word) > 1 and word[0] in _PUNCTUATION:
            words += [word[0], word[1:]]
        else:
            words.append(word)
    return words


def _ngrams(text: str, char_order: int, word_order: int) -> list[Counter]:
    chars = "".join(text.split())
    counters = [
        Counter(chars[i : i + n] for i in range(len(chars) - n + 1))
        for n in range(1, char_order + 1)
    ]
    words = _words(text)
    counters += [
        Counter(" ".join(words[i : i + n]) for i in range(len(words) - n + 1))
        for n in range(1, word_order + 1)
    ]
    return counters


def chrf_statistics(
    prediction: str, reference: str, char_order: int = 6, word_order: int = 2
) -> list[int]:
    """[prediction count, reference count, matches] for each n-gram order."""
    stats: list[int] = []
    pairs = zip(
        _ngrams(canonical(prediction), char_order, word_order),
        _ngrams(canonical(reference), char_order, word_order),
        strict=True,
    )
    for hyp, ref in pairs:
        matches = sum(min(count, ref[gram]) for gram, count in hyp.items() if gram in ref)
        stats += [sum(hyp.values()) if ref else 0, sum(ref.values()), matches]
    return stats


def _f_score(stats: list[int], beta: float = 2.0) -> float:
    precision = recall = 0.0
    orders = 0
    for i in range(0, len(stats), 3):
        n_hyp, n_ref, n_match = stats[i : i + 3]
        if n_hyp > 0 and n_ref > 0:
            precision += n_match / n_hyp
            recall += n_match / n_ref
            orders += 1
    if orders == 0:
        return 0.0
    precision, recall = precision / orders, recall / orders
    if precision + recall == 0:
        return 0.0
    factor = beta**2
    return 100 * (1 + factor) * precision * recall / (factor * precision + recall)


def chrf(prediction: str, reference: str) -> float:
    """Sentence-level chrF++ (0 to 100) on canonical text."""
    return _f_score(chrf_statistics(prediction, reference))


def corpus_chrf(pairs: list[tuple[str, str]]) -> float:
    """Corpus-level chrF++: statistics summed over all pairs before the F-score."""
    totals: list[int] = []
    for prediction, reference in pairs:
        stats = chrf_statistics(prediction, reference)
        totals = [a + b for a, b in zip(totals, stats, strict=True)] if totals else stats
    return _f_score(totals) if totals else 0.0


# --- word segmentation -----------------------------------------------------------------


def _split(text: str) -> tuple[str, set[int]]:
    """Text without separators, and the offsets where a separator (space or ZWSP) stood."""
    parts = [part for part in _SEPARATORS.split(normalize(text).strip()) if part]
    boundaries, offset = set(), 0
    for part in parts[:-1]:
        offset += len(part)
        boundaries.add(offset)
    return "".join(parts), boundaries


def boundary_f1(prediction: str, reference: str) -> float:
    """F1 of word boundaries (space or ZWSP). 0 if the model changed the text itself."""
    pred_chars, pred_bounds = _split(prediction)
    ref_chars, ref_bounds = _split(reference)
    if pred_chars != ref_chars:
        return 0.0
    if not pred_bounds and not ref_bounds:
        return 1.0
    hits = len(pred_bounds & ref_bounds)
    if hits == 0:
        return 0.0
    precision, recall = hits / len(pred_bounds), hits / len(ref_bounds)
    return 2 * precision * recall / (precision + recall)
