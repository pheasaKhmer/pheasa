"""Throughput of `normalize`, `normalize(report=True)` and `validate`, in MB/s of UTF-8.

The input is synthetic: random consonants, subscripts and marks typed in random order,
separated by spaces, ZWSP and some digits and Latin. It is benchmark filler, not Khmer
language data, and is generated on the fly from a fixed seed.

    python scripts/bench_throughput.py            # print MB/s
    python scripts/bench_throughput.py --check    # also fail on a regression

`--check` fails if a mode is superlinear (4x the input takes more than 8x the time),
which does not depend on how fast the machine is, or if it drops below a floor set well
under what a CI runner achieves. With GITHUB_STEP_SUMMARY set, the results are added to
the CI job summary.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from collections.abc import Callable

from pheasa import normalize, validate

CONSONANTS = [chr(cp) for cp in range(0x1780, 0x17A3)]
MARKS = [chr(cp) for cp in range(0x17B6, 0x17C6)] + ["ំ", "៉", "៊", "៌"]
SEPARATORS = [" ", "​", "", "", "១២", " abc "]

MODES: dict[str, Callable[[str], object]] = {
    "normalize": normalize,
    "report": lambda text: normalize(text, report=True),
    "validate": validate,
}
# MB/s. Local runs (Apple M-series, Python 3.12) reach about 7, 1 and 13.
FLOORS = {"normalize": 1.0, "report": 0.2, "validate": 2.0}
MAX_GROWTH = 8.0  # time ratio allowed for 4x the input; linear is about 4


def synthetic_text(syllables: int, seed: int = 0) -> str:
    rng = random.Random(seed)
    parts = []
    for _ in range(syllables):
        parts.append(rng.choice(CONSONANTS))
        marks = rng.sample(MARKS, rng.choice([0, 1, 1, 2]))
        if rng.random() < 0.3:
            marks.insert(rng.randrange(len(marks) + 1), "្" + rng.choice(CONSONANTS))
        parts += marks
        parts.append(rng.choice(SEPARATORS))
    return "".join(parts)


def best_time(function: Callable[[str], object], text: str, repeats: int) -> float:
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        function(text)
        best = min(best, time.perf_counter() - start)
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--syllables", type=int, default=20_000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    small = synthetic_text(args.syllables)
    large = synthetic_text(4 * args.syllables)
    megabytes = len(large.encode("utf-8")) / 1e6
    rows, failures = [], []
    for name, function in MODES.items():
        small_time = best_time(function, small, args.repeats)
        large_time = best_time(function, large, args.repeats)
        speed, growth = megabytes / large_time, large_time / small_time
        rows.append((name, speed, growth))
        if growth > MAX_GROWTH:
            failures.append(f"{name}: 4x input took {growth:.1f}x the time")
        if speed < FLOORS[name]:
            failures.append(f"{name}: {speed:.2f} MB/s is below the {FLOORS[name]} floor")

    python = sys.version.split()[0]
    lines = [
        f"Throughput on {megabytes:.2f} MB of synthetic text (Python {python})",
        "",
        "| mode | MB/s | time for 4x input |",
        "|---|---|---|",
        *(f"| {name} | {speed:.2f} | {growth:.1f}x |" for name, speed, growth in rows),
    ]
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    if args.check and failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
