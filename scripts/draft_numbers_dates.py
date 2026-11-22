"""Draft numbers-and-dates items by rule, for a native speaker to verify and promote.

    uv run python scripts/draft_numbers_dates.py \
        --instructions-km bench/drafts/numbers-and-dates/instructions-km.toml \
        --out bench/drafts/numbers-and-dates/drafts.jsonl

Every Khmer answer is computed from Unicode CLDR 49 (data/cldr-km/km.json): number
words from the `%spellout-numbering` rules, month names and the long date pattern
`d MMMM y`. Digits are converted with `pheasa.normalize(..., digits=...)`. Nothing is
written from memory. The Khmer instructions are not in this file: they come from
`--instructions-km` (a local, unverified draft file); without it, `instruction_km` is
left empty.

Item types: digits to Khmer digits, Khmer digits to digits, number to Khmer words, Khmer
words to number, English date to Khmer date, Khmer date to ISO date. Output is
deterministic for a given --seed. Drafts are never scored; only a person promotes them.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import tomllib
from datetime import date, timedelta
from pathlib import Path

from pheasa import normalize

CLDR = Path("data/cldr-km/km.json")
ZWSP = "​"
TASK = "numbers-and-dates"

# English instructions per item type, and how many drafts of each to make (out of 250).
TYPES = {
    "digits-to-khmer-digits": ("Write this number with Khmer digits.", 40),
    "khmer-digits-to-digits": ("Write this number with Arabic digits (0-9).", 30),
    "number-to-words": ("Write this number in Khmer words.", 75),
    "words-to-number": ("Write this Khmer number with Arabic digits (0-9).", 40),
    "date-to-khmer": (
        "Write this date in Khmer, in the form used in Cambodian documents (with Khmer digits).",
        40,
    ),
    "khmer-date-to-iso": ("Write this date in the form YYYY-MM-DD with Arabic digits.", 25),
}
# Number sizes, as (low, high, share): every size of the spell-out rules is covered.
SIZES = [
    (0, 10, 0.08),
    (11, 99, 0.2),
    (100, 999, 0.2),
    (1_000, 9_999, 0.2),
    (10_000, 99_999, 0.12),
    (100_000, 999_999, 0.12),
    (1_000_000, 999_999_999, 0.08),
]
MONTHS_EN = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


class Spellout:
    """The subset of ICU rule-based number formatting that CLDR's Khmer rules use.

    Source: UTS #35 Part 3, "Rule-Based Number Formatting": a rule applies from its base
    value up to the next rule's; its divisor is the largest power of 10 not above the
    base; `<<` formats the quotient and `>>` the remainder with the same rule set;
    text in `[...]` is omitted when the remainder is 0; `=%name=` formats the whole
    number with another rule set.
    """

    def __init__(self, rulesets: dict[str, str]) -> None:
        self.rules: dict[str, list[tuple[int, str]]] = {}
        for name, text in rulesets.items():
            rules = []
            for line in text.split(";"):
                key, _, body = line.strip().partition(": ")
                if key.isdigit():  # skip "-x" (negative) and "x.x" (fraction) rules
                    rules.append((int(key), body))
            self.rules[name] = sorted(rules)

    def format(self, n: int, ruleset: str = "spellout-numbering") -> str:
        if n < 0:
            raise ValueError("only non-negative integers are drafted")
        base, body = [rule for rule in self.rules[ruleset] if rule[0] <= n][-1]
        whole = re.fullmatch(r"(.*)=(%[\w-]+|[#,0]+)=(.*)", body)
        if whole:
            if not whole[2].startswith("%"):
                raise ValueError(f"{n} is beyond the spell-out rules (decimal fallback)")
            return whole[1] + self.format(n, whole[2][1:]) + whole[3]
        quotient, remainder = divmod(n, 10 ** (len(str(base)) - 1) if base else 1)
        body = re.sub(r"\[(.*?)\]", lambda m: m[1] if remainder else "", body)
        return re.sub(
            r"<<|>>",
            lambda m: self.format(quotient if m[0] == "<<" else remainder, ruleset),
            body,
        )


def khmer_digits(text: str) -> str:
    return normalize(text, digits="khmer")


def pick_numbers(rng: random.Random, count: int) -> list[int]:
    numbers: list[int] = []
    for low, high, share in SIZES:
        wanted = max(1, round(count * share))
        while wanted and len(numbers) < count:
            n = rng.randint(low, high)
            if n not in numbers:
                numbers.append(n)
                wanted -= 1
    while len(numbers) < count:  # rounding left a gap
        n = rng.randint(11, 9_999)
        if n not in numbers:
            numbers.append(n)
    rng.shuffle(numbers)
    return numbers


def pick_dates(rng: random.Random, count: int) -> list[date]:
    start, days = date(1950, 1, 1), (date(2035, 12, 31) - date(1950, 1, 1)).days
    picked: list[date] = []
    while len(picked) < count:
        day = start + timedelta(days=rng.randint(0, days))
        if day not in picked:
            picked.append(day)
    return picked


def khmer_long_date(day: date, cldr: dict) -> str:
    """CLDR's long pattern `d MMMM y` with the native (Khmer) digits."""
    if cldr["date_patterns"]["long"] != "d MMMM y" or cldr["native_numbering"] != "khmr":
        raise ValueError("CLDR long date pattern changed; review this function")
    month = cldr["months_wide"][day.month - 1]
    return f"{khmer_digits(str(day.day))} {month} {khmer_digits(str(day.year))}"


def drafts(cldr: dict, instructions_km: dict, seed: int, total: int) -> list[dict]:
    rng = random.Random(seed)
    spell = Spellout(cldr["spellout"])
    scale = total / sum(n for _, n in TYPES.values())
    counts = {kind: round(n * scale) for kind, (_, n) in TYPES.items()}
    km_extra_forms = instructions_km.get("date-to-khmer", {}).get("extra_forms", [])
    cldr_source = f"Unicode CLDR {cldr['cldr'].removeprefix('release-')} ({CLDR})"
    manifest = CLDR.with_name("manifest.jsonl").read_text(encoding="utf-8").splitlines()
    retrieved = json.loads(manifest[0])["retrieved"]
    records = []

    def add(kind: str, text: str, reference: str | list[str], transform: str, notes: str):
        km = instructions_km.get(kind, {}).get("km", "")
        records.append(
            {
                "task": TASK,
                "item_type": kind,
                "input": {"instruction_en": TYPES[kind][0], "instruction_km": km, "text": text},
                "reference": reference,
                "source": cldr_source,
                "license": "CC-BY-4.0",
                "retrieved": retrieved,
                "transform": transform,
                "generated_by": "scripts/draft_numbers_dates.py",
                "notes": notes,
                "verified": False,
                **({"authored_by": instructions_km["authored_by"]} if km else {}),
            }
        )

    for n in pick_numbers(rng, counts["digits-to-khmer-digits"]):
        add(
            "digits-to-khmer-digits",
            str(n),
            khmer_digits(str(n)),
            "digits mapped one to one to U+17E0..17E9",
            "mechanical",
        )
    for n in pick_numbers(rng, counts["khmer-digits-to-digits"]):
        add(
            "khmer-digits-to-digits",
            khmer_digits(str(n)),
            str(n),
            "digits mapped one to one from U+17E0..17E9",
            "mechanical",
        )
    review_words = (
        "words from CLDR %spellout-numbering (ZWSP between words removed); "
        "add every other accepted spelling, e.g. other words for 10,000 or 100,000"
    )
    for n in pick_numbers(rng, counts["number-to-words"]):
        words = spell.format(n).replace(ZWSP, "")
        add("number-to-words", str(n), words, "CLDR %spellout-numbering", review_words)
    for n in pick_numbers(rng, counts["words-to-number"]):
        words = spell.format(n).replace(ZWSP, "")
        add("words-to-number", words, str(n), "CLDR %spellout-numbering", review_words)
    for day in pick_dates(rng, counts["date-to-khmer"]):
        cldr_form = khmer_long_date(day, cldr)
        month = cldr["months_wide"][day.month - 1]
        extra = [
            form.format(
                day=khmer_digits(str(day.day)), month=month, year=khmer_digits(str(day.year))
            )
            for form in km_extra_forms
        ]
        add(
            "date-to-khmer",
            f"{day.day} {MONTHS_EN[day.month - 1]} {day.year}",
            [cldr_form, *extra],
            "CLDR long date pattern d MMMM y with Khmer digits"
            + ("; later references from unverified templates" if extra else ""),
            "first reference is CLDR's; check every reference and add accepted forms",
        )
    for day in pick_dates(rng, counts["khmer-date-to-iso"]):
        add(
            "khmer-date-to-iso",
            khmer_long_date(day, cldr),
            day.isoformat(),
            "CLDR long date pattern d MMMM y with Khmer digits",
            "mechanical once the month names are confirmed",
        )
    for number, record in enumerate(records, start=1):
        record["id"] = f"{TASK}-v1d{number:04d}"
    return [{"id": r.pop("id"), **r} for r in records]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--instructions-km", help="local TOML of draft Khmer instructions")
    parser.add_argument("--count", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20261123)
    args = parser.parse_args(argv)
    if "drafts" not in Path(args.out).parts:
        parser.error("drafts go to bench/drafts/ only; a person promotes them to bench/items/")
    cldr = json.loads(CLDR.read_text(encoding="utf-8"))
    instructions = {}
    if args.instructions_km:
        instructions = tomllib.loads(Path(args.instructions_km).read_text(encoding="utf-8"))
    records = drafts(cldr, instructions, args.seed, args.count)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    kinds = {kind: sum(r["item_type"] == kind for r in records) for kind in TYPES}
    print(f"wrote {len(records)} drafts to {out}: {kinds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
