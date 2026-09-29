"""Download the approved Phase 2 sources into data/raw/ and record provenance (Q-014).

    uv run python scripts/fetch_sources.py [NAME ...]    # default: all

Each file lands in data/raw/<name>/ (not committed). Its provenance (source, license,
retrieval date, SHA-256) is appended to data/<name>/manifest.jsonl, which is committed.
Files already present are not fetched again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

USER_AGENT = "pheasa-research/0.1 (https://github.com/pheasaKhmer/pheasa)"
NTREX = "https://raw.githubusercontent.com/MicrosoftTranslator/NTREX/main/NTREX-128/"
HF = "https://huggingface.co/"

SOURCES = {
    "ntrex": {
        "license": "CC-BY-SA-4.0",
        "page": "https://github.com/MicrosoftTranslator/NTREX",
        "files": [NTREX + "newstest2019-ref.khm.txt", NTREX + "newstest2019-src.eng.txt"],
    },
    "fineweb2-khm": {
        "license": "ODC-By-1.0",
        "page": HF + "datasets/HuggingFaceFW/fineweb-2",
        "files": [
            HF
            + "datasets/HuggingFaceFW/fineweb-2/resolve/main/data/khm_Khmr/test/000_00000.parquet"
        ],
    },
    "kmwiki": {
        "license": "CC-BY-SA-4.0",
        "page": "https://dumps.wikimedia.org/kmwiki/",
        "files": ["https://dumps.wikimedia.org/kmwiki/latest/kmwiki-latest-pages-articles.xml.bz2"],
    },
    "tokenizers": {
        "license": "per file: Apache-2.0 (mT5), CC-BY-NC-4.0 (NLLB); used only to count tokens",
        "page": HF,
        "files": [
            HF + "google/mt5-base/resolve/main/spiece.model",
            HF + "facebook/nllb-200-distilled-600M/resolve/main/sentencepiece.bpe.model",
        ],
    },
}


def download(url: str, target: Path) -> str:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as out:
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", default=list(SOURCES))
    args = parser.parse_args(argv)
    for name in args.names:
        source = SOURCES[name]
        raw, manifest = Path("data/raw") / name, Path("data") / name / "manifest.jsonl"
        raw.mkdir(parents=True, exist_ok=True)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        for url in source["files"]:
            prefix = url.split("/")[-4] + "-" if name == "tokenizers" else ""
            target = raw / (prefix + url.split("/")[-1])
            if target.exists():
                print(f"present: {target}")
                continue
            sha256 = download(url, target)
            record = {
                "source": url,
                "page": source["page"],
                "license": source["license"],
                "retrieved": date.today().isoformat(),
                "transform": "none (downloaded as published)",
                "file": str(target),
                "sha256": sha256,
            }
            with manifest.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
            print(f"fetched: {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
