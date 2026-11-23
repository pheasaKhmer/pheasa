"""Fetch Unicode CLDR's Khmer locale data and extract what numbers-and-dates needs.

    uv run python scripts/extract_cldr_km.py

Downloads three files from the pinned CLDR release into data/raw/cldr-km/ (not
committed), then writes the committed extract data/cldr-km/km.json, a copy of the
Unicode license (data/cldr-km/LICENSE) and a provenance manifest. The extract keeps the
source text unchanged: the spell-out rules verbatim, the wide month and weekday names
of the Gregorian calendar (format context), the date patterns and the native numbering
system.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

RELEASE = "release-49"
BASE = f"https://raw.githubusercontent.com/unicode-org/cldr/{RELEASE}/"
FILES = {
    "rbnf-km.xml": BASE + "common/rbnf/km.xml",
    "main-km.xml": BASE + "common/main/km.xml",
    "LICENSE": BASE + "LICENSE",
}
RAW, OUT = Path("data/raw/cldr-km"), Path("data/cldr-km")
USER_AGENT = "pheasa-research/0.1 (https://github.com/pheasaKhmer/pheasa)"
DAYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")


def fetch(url: str, target: Path) -> str:
    if not target.exists():
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
    return hashlib.sha256(target.read_bytes()).hexdigest()


def rulesets(rbnf: ET.Element) -> dict[str, str]:
    """Each %ruleset in the SpelloutRules grouping, as its verbatim rule text."""
    text = rbnf.find(".//rulesetGrouping[@type='SpelloutRules']/rbnfRules").text
    found = {}
    for block in re.split(r"\n(?=%)", text.strip()):
        name, _, body = block.partition(":\n")
        found[name.lstrip("%")] = body.strip()
    return found


def extract(rbnf: ET.Element, main: ET.Element) -> dict:
    greg = main.find(".//calendar[@type='gregorian']")
    months = greg.find("months/monthContext[@type='format']/monthWidth[@type='wide']")
    days = greg.find("days/dayContext[@type='format']/dayWidth[@type='wide']")
    patterns = {
        length.get("type"): length.find("dateFormat/pattern").text
        for length in greg.find("dateFormats").findall("dateFormatLength")
    }
    by_type = {d.get("type"): d.text for d in days}
    return {
        "spellout": rulesets(rbnf),
        "months_wide": [m.text for m in sorted(months, key=lambda m: int(m.get("type")))],
        "days_wide": [by_type[d] for d in DAYS],
        "day_order": list(DAYS),
        "date_patterns": patterns,
        "native_numbering": main.find("numbers/otherNumberingSystems/native").text,
    }


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    digests = {name: fetch(url, RAW / name) for name, url in FILES.items()}
    data = extract(ET.parse(RAW / "rbnf-km.xml").getroot(), ET.parse(RAW / "main-km.xml").getroot())
    retrieved = date.today().isoformat()
    record = {
        "cldr": RELEASE,
        "license": "Unicode-3.0",
        "copyright": "Copyright © 1991-2026 Unicode, Inc.",
        "sources": {name: {"url": FILES[name], "sha256": digests[name]} for name in FILES},
        **data,
    }
    (OUT / "km.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (OUT / "LICENSE").write_bytes((RAW / "LICENSE").read_bytes())
    manifest = [
        {
            "source": FILES[name],
            "page": "https://cldr.unicode.org/",
            "license": "Unicode-3.0",
            "retrieved": retrieved,
            "transform": "spell-out rules, wide Gregorian month and day names, date patterns "
            "and native numbering system extracted verbatim into data/cldr-km/km.json",
            "file": str(RAW / name),
            "sha256": digests[name],
        }
        for name in ("rbnf-km.xml", "main-km.xml")
    ]
    (OUT / "manifest.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in manifest), encoding="utf-8"
    )
    print(f"wrote {OUT / 'km.json'} from CLDR {RELEASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
