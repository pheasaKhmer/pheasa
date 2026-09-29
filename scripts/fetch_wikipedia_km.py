"""Fetch a sample of Khmer Wikipedia articles as plain text for fixture drafting.

    uv run python scripts/fetch_wikipedia_km.py --pages 100

Random main-namespace articles are fetched through the MediaWiki API (TextExtracts,
plain text). Text goes to data/raw/wikipedia-km/ (not committed). Each article gets a
provenance record in data/wikipedia-km/manifest.jsonl with its revision URL. Khmer
Wikipedia text is licensed CC BY-SA 4.0 (siteinfo rightsinfo, checked 2026-09-30).
Requests are sequential, throttled and identified, per the Wikimedia API etiquette.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API = "https://km.wikipedia.org/w/api.php"
USER_AGENT = "pheasa-fixtures/0.1 (https://github.com/pheasaKhmer/pheasa)"
LICENSE = "CC-BY-SA-4.0"
DELAY = 1.0  # seconds between requests


def api(**params: str) -> dict:
    query = urllib.parse.urlencode(
        {"format": "json", "formatversion": "2", "maxlag": "5", **params}
    )
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    time.sleep(DELAY)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data


def random_titles(count: int) -> list[str]:
    titles: list[str] = []
    while len(titles) < count:
        batch = api(action="query", list="random", rnnamespace="0", rnlimit="20")
        titles += [
            page["title"] for page in batch["query"]["random"] if page["title"] not in titles
        ]
    return titles[:count]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", type=int, default=100)
    parser.add_argument("--raw", default="data/raw/wikipedia-km")
    parser.add_argument("--manifest", default="data/wikipedia-km/manifest.jsonl")
    args = parser.parse_args(argv)

    raw, manifest = Path(args.raw), Path(args.manifest)
    raw.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    known = set()
    if manifest.exists():
        known = {json.loads(line)["pageid"] for line in manifest.read_text().splitlines() if line}
    today = date.today().isoformat()
    fetched = 0
    with manifest.open("a", encoding="utf-8") as out:
        for title in random_titles(args.pages):
            page = api(action="query", prop="extracts|info", explaintext="1", titles=title)
            page = page["query"]["pages"][0]
            text = page.get("extract", "")
            if page.get("missing") or not text.strip() or page["pageid"] in known:
                continue
            (raw / f"{page['pageid']}.txt").write_text(text, encoding="utf-8")
            record = {
                "pageid": page["pageid"],
                "title": page["title"],
                "source": f"https://km.wikipedia.org/w/index.php?oldid={page['lastrevid']}",
                "license": LICENSE,
                "retrieved": today,
                "transform": "MediaWiki TextExtracts plain text (explaintext=1)",
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            known.add(page["pageid"])
            fetched += 1
    print(f"fetched {fetched} articles into {raw}; manifest {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
