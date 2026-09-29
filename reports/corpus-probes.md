# Corpus probes: how often Khmer text needs normalization (September 2026)

*Samputhy Khim* · **Status:** draft for review

Two questions, measured on real Khmer text:

1. How much Khmer text is stored in a non-canonical order or form, the problem
   `pheasa.normalize` fixes?
2. How often do legacy lunar-date sequences (digit + coeng + khan) occur? The answer
   decides whether normalization should convert them (decision D-009).

## Corpora

| Corpus | License | Size | Retrieved |
|---|---|---|---|
| FineWeb-2 `khm_Khmr`, test split (web crawl) | ODC-By 1.0 | 16,337 documents, 34.5M characters | 2026-09-30 |
| Khmer Wikipedia, full dump (`kmwiki-latest-pages-articles`, with markup) | CC BY-SA 4.0 | 134.9M characters | 2026-09-30 |
| Khmer Wikipedia, random sample of 146 articles (plain text) | CC BY-SA 4.0 | 3,824 sentences | 2026-09-30 |
| NTREX-128 Khmer (professional news translation) | CC BY-SA 4.0 | 1,997 sentences | 2026-09-30 |

Raw text is not in the repository. The fetch scripts and manifests under `data/` record
exactly what was retrieved.

## 1. Non-canonical text

A syllable is non-canonical if `normalize` (version 1) would change it.

| Corpus | Syllables | Non-canonical | Syllable types seen in 2+ encodings | Units changed |
|---|---|---|---|---|
| FineWeb-2 (web) | 15.9M | 0.34% | 666 of 4,775 | **61% of documents** |
| Wikipedia, full dump | 22.3M | 0.52% | 1,076 of 8,347 | — |
| Wikipedia, sample | 235,901 | 0.61% | 117 of 1,982 | 13% of sentences |
| NTREX (translation) | 131,562 | 0.12% | 45 of 1,471 | 7% of sentences |

About one syllable in two to three hundred is non-canonical, but the variants are spread
thinly across the text: six in ten web documents contain at least one. In FineWeb-2, the
syllables that occur in more than one encoding account for 2.2 million of the 15.9
million syllables, so a large share of all running text is made of syllables that also
appear in some other byte sequence elsewhere in the corpus.

Documents in FineWeb-2 changed by each rule of the specification:

| Rule | What it fixes | Documents |
|---|---|---|
| 3.8 | coeng da stored where coeng ta is canonical | 7,149 |
| 3.7 | two subscripts with coeng ro first | 3,667 |
| 2.2 | marks typed out of order | 1,959 |
| 3.6 | -u typed where a consonant shifter was meant | 728 |
| 3.3 | a split vowel typed as two parts | 421 |
| 3.4, 3.5, 3.1 | other "do not use" sequences | 53 |

Edited and translated text is cleaner than web text, as expected: professional news
translations need changes in 7% of sentences, a Wikipedia sample in 13%.

## 2. Legacy lunar-date sequences (D-009)

Unicode Technical Note #61 (p. 35) describes an old way of writing lunar dates as
digit + coeng + khan, now replaced by the symbols U+19E0–19FF.

- **Full sequences found: none**, in about 169 million characters (FineWeb-2 test split
  and the full Wikipedia dump), counting the two-digit form with a leading ១.
- **The modern lunar symbols** U+19E0–19FF appear 16 times.
- **Partial matches** occur 14 times. Twelve are a consonant, a coeng, then a khan (a
  subscript sign with nothing under it, just before the full stop). Two are a digit
  followed by a coeng and then a letter or ASCII digits (for example `២០១៤្014`). By
  their structure these look like typing slips rather than dates; this has not yet been
  confirmed by a native speaker.

**Conclusion for D-009:** in these corpora the legacy form is effectively absent, so
flagging it rather than converting it (normalization version 1) loses nothing. OCR
output of printed material, where such sequences have been reported, was not covered
and remains the place to look.

## Reproducing

```bash
uv sync --group research
uv run python scripts/fetch_sources.py fineweb2-khm kmwiki ntrex
uv run python scripts/fetch_wikipedia_km.py --pages 150
uv run python scripts/encoding_variants.py data/raw/fineweb2-khm --top 10
uv run python scripts/lunar_probe.py data/raw/fineweb2-khm data/raw/kmwiki --out sample.jsonl
```

The Wikipedia sample was drawn at random on 2026-09-30; its article revisions are listed
in `data/wikipedia-km/manifest.jsonl`. Document-level counts come from running
`normalize(text, report=True)` on each FineWeb-2 document.
