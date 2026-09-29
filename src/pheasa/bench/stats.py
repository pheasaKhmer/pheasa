"""Bootstrap confidence intervals for benchmark scores (seeded, so reproducible)."""

from __future__ import annotations

import random
from collections.abc import Sequence

__all__ = ["bootstrap_ci", "paired_difference_ci"]


def _percentiles(values: list[float], level: float) -> tuple[float, float]:
    values.sort()
    low = int((1 - level) / 2 * len(values))
    high = int((1 + level) / 2 * len(values)) - 1
    return values[low], values[high]


def bootstrap_ci(
    scores: Sequence[float], level: float = 0.95, samples: int = 10_000, seed: int = 0
) -> tuple[float, float, float]:
    """Mean score and its percentile bootstrap interval: (mean, low, high)."""
    if not scores:
        raise ValueError("no scores")
    rng, n = random.Random(seed), len(scores)
    means = [sum(scores[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples)]
    return (sum(scores) / n, *_percentiles(means, level))


def paired_difference_ci(
    a: Sequence[float],
    b: Sequence[float],
    level: float = 0.95,
    samples: int = 10_000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Mean of a - b over the same items, with a paired bootstrap interval.

    If the interval contains 0, the two systems are not distinguishable on these items.
    """
    if len(a) != len(b):
        raise ValueError("paired scores must cover the same items")
    return bootstrap_ci([x - y for x, y in zip(a, b, strict=True)], level, samples, seed)
