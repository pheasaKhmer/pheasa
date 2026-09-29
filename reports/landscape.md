# Khmer language technology: a landscape (September 2026)

*Samputhy Khim* · **Status:** draft for review · Data: [`landscape.jsonl`](landscape.jsonl)

This report lists the public datasets, tools, models and benchmarks for Khmer (`khm`,
Khmer script) that a Khmer language technology project can build on, and the gaps
between them. It is the starting map for Pheasa's benchmark and corpus work.

## Method

- **Sources.** The [awesome-khmer-language](https://github.com/seanghay/awesome-khmer-language)
  index, then searches of Hugging Face, GitHub and the ACL Anthology for resources it
  does not list, with emphasis on 2023–2026. Only resources that could be opened are
  included; each row links to its primary source (repository, dataset or model card).
- **Licenses.** Every license was checked on 2026-09-30 at the URL recorded in
  `license_url`: the Hugging Face metadata record, the GitHub license record, or the
  license page itself. One claim was corrected (ICU). Where no license could be found,
  the row says `unknown`; unknown does not mean free to use.
- **Quality notes** are factual statements from the source (for example "machine
  translated from English"). They are not judgments of the Khmer text, which has not
  been reviewed. Rows marked with a confidence below high say why.
- **Not covered:** resources behind logins or paywalls, and models whose Khmer support
  could not be confirmed from their own documentation (for example Gemma 3, Qwen3 and
  Seamless M4T v2 were left out rather than guessed).

## Summary

- **Speech is comparatively well served.** Several openly licensed Khmer ASR datasets
  (CC BY-SA 4.0) were updated in 2026, alongside FLEURS and OpenSLR, and there are
  fine-tuned Whisper, wav2vec2 and Qwen3-ASR models. Open text-to-speech is weaker: the
  models found are non-commercial or undocumented.
- **Raw text exists, clean licensed text less so.** Crawled corpora (FineWeb-2, mC4,
  CC-100, CulturaX) include Khmer, and several Khmer-only collections were updated in
  2026.
  Many community datasets state no source or no license.
- **Evaluation is the thinnest layer.** The multilingual benchmarks that include Khmer
  (FLORES, Belebele, SIB-200, NTREX) are translations of English material. No
  Khmer-native LLM benchmark with released data was found.
- **Licenses are a real constraint.** A fifth of the resources have no license that
  could be found, and several of the most useful ones are non-commercial (NLLB-200,
  MMS, the Khmer part of the Asian Language Treebank).

## Gap analysis

1. **No Khmer-native benchmark for language models.** Global-MMLU covers 42 languages
   and not Khmer (checked in its Hugging Face configuration list). SEA-HELM lists Khmer
   tasks (multiple-choice QA, instruction following and MT-Bench, per its README);
   whether its items were written in Khmer or translated was not verified. Belebele and
   SIB-200 are built on FLORES sentences translated from English. This is the gap
   Pheasa's benchmark (roadmap Phase 4) is meant to fill.
2. **Contamination-safe evaluation needs gating.** FLORES+ and FLORES-200 are gated on
   Hugging Face to limit training contamination. Any new Khmer test set needs the same
   care: a canary string and a held-out part.
3. **Task datasets are missing or silver-standard.** The only named-entity data found is
   WikiANN's automatically derived Khmer split. No sentiment dataset with a license and
   no Khmer instruction-tuning dataset with a clear license were found.
4. **Parallel data is fragmented by license.** The Khmer–English data with the clearest
   provenance is split between CC BY 4.0 (ALT parallel corpus), CC BY-NC-SA 4.0 (the
   Khmer ALT treebank), a signed agreement (ECCC) and unstated terms (several community
   collections).
5. **Provenance is often missing.** Many community datasets on Hugging Face do not say
   where their text came from, and some declare a permissive license over material they
   do not own (textbooks, newspapers, YouTube). Users should treat the declared license
   as a claim.
6. **Normalization has tools but no shared test suite.** SIL's `khmer-normalizer`,
   `seanghay/khmernormalizer` and `KhmerSyllableReordering` exist, but no public set of
   verified before/after examples was found. Pheasa's verified golden fixtures are a
   first step, and the datasets above were built without a common normalization, so
   duplicates and encoding variants across them are likely.
7. **Segmentation remains an open choice.** At least five word segmenters exist
   (khmer-nltk, khmercut, a CRF model, a neural segmenter and a dictionary-based one),
   with no common evaluation set found.

## Resources

<!-- tables:start -->
98 resources. License groups (each checked at the source on the date in `license_check`):

| License group | Resources |
|---|---|
| Permissive | 54 |
| Share-alike or copyleft | 14 |
| Non-commercial | 6 |
| Unknown (no license found) | 19 |
| Custom, mixed or by agreement | 5 |

### Benchmarks (7)

| Name | Purpose | Khmer | Size | License | Access | Updated | Notes |
|---|---|---|---|---|---|---|---|
| [Belebele (khm_Khmr)](https://huggingface.co/datasets/facebook/belebele) | Multiple-choice reading comprehension in 122 language variants; khm_Khmr split | multilingual | khm_Khmr split size unknown | CC-BY-SA-4.0 | open | 2024-08 | Passages from FLORES-200; questions human-written in English then translated. |
| [FLORES+ (openlanguagedata/flores_plus)](https://huggingface.co/datasets/openlanguagedata/flores_plus) | Multilingual MT evaluation sets (dev, devtest) including khm_Khmr | multilingual | khm_Khmr dev and devtest splits; sentence counts unknown | CC-BY-SA-4.0 | gated | 2026-07 | Auto-gated with integrity protections against training contamination; human-translated Wikipedia-sourced sentences. |
| [FLORES-200 (facebook/flores)](https://huggingface.co/datasets/facebook/flores) | 200-language MT evaluation benchmark including khm_Khmr | multilingual | khm_Khmr dev and devtest; counts unknown | CC-BY-SA-4.0 | gated | 2026-05 | Auto-gated; khm_Khmr present in config list. |
| [Khmer OCR Benchmark Dataset (KHOB)](https://github.com/EKYCSolutions/khmer-ocr-benchmark-dataset) | OCR benchmark with clean digital, scene text and handwritten levels plus evaluation script | only | unknown | MIT | open | 2026-01 | Data hosted on Google Drive links from the README; size not stated in repo. |
| [NTREX-128 (khm)](https://github.com/MicrosoftTranslator/NTREX) | English-to-128-language news MT test references; includes Khmer file | multilingual | newstest2019-ref.khm.txt, 805,424 bytes | CC-BY-SA-4.0 | open | 2024-06 | Human translations of English news test set; Khmer file confirmed in NTREX-128 directory listing. |
| [SEA-HELM](https://github.com/aisingapore/SEA-HELM) | Southeast Asian LLM evaluation suite; Khmer MCQA, SEA-IFEval and SEA MT-Bench added 2026-01 | multilingual | unknown | MIT | open | 2026-08 | README changelog lists Khmer under a 20 Jan 2026 update; Khmer item origin (native or translated) not checked. (confidence medium: Khmer claim from README changelog only; item counts and construction not checked.) |
| [SIB-200 (khm_Khmr)](https://huggingface.co/datasets/Davlan/sib200) | Topic classification benchmark over 200 languages; khm_Khmr config | multilingual | khm_Khmr size unknown | CC-BY-SA-4.0 | open | 2024-02 | Built on FLORES-200 sentences with topic labels. |

### Datasets (42)

| Name | Purpose | Khmer | Size | License | Access | Updated | Notes |
|---|---|---|---|---|---|---|---|
| [Asian Language Treebank (ALT) Project](https://www2.nict.go.jp/astrec-att/member/mutiyama/ALT/) | Wikinews sentences translated into 12 Asian languages incl. Khmer; parallel plus treebanks | multilingual | ~20,106 parallel sentences (18,088 train / 1,000 dev / 1,018 test) | CC BY 4.0 (parallel corpus); CC BY-NC-SA 4.0 (Khmer treebank as stated on page) | open | 2019-12 | Human translation of English Wikinews (CC BY 2.5 source); Khmer treebank license differs from parallel corpus. |
| [CC-100 (km)](https://huggingface.co/datasets/statmt/cc100) | Monolingual Common Crawl corpus for 100+ languages including Khmer | multilingual | unknown | unknown | open | 2024-03 | Crawled text; HF card metadata carries no license field. |
| [CulturaX (km)](https://huggingface.co/datasets/uonlp/CulturaX) | Cleaned multilingual web corpus (mC4 + OSCAR), 167 languages; km config | multilingual | unknown | unknown | gated | 2024-12 | Auto-gated with form; no license field in card metadata, only an 'as is' gating prompt. |
| [Digital-Divide-Data/khm-asr-cultural (v1)](https://huggingface.co/datasets/Digital-Divide-Data/khm-asr-cultural) | Khmer ASR cultural-topic speech-text pairs (earlier release; old id DDD-Cambodia/khm-asr-cultural) | only | 134.6 hours / 56,716 train examples / 66.6 GB | CC-BY-SA-4.0 | open | 2026-04 | Card says manually curated by native speakers; repo id redirected from DDD-Cambodia namespace. |
| [Digital-Divide-Data/khmer-speech-dataset](https://huggingface.co/datasets/Digital-Divide-Data/khmer-speech-dataset) | Curated Khmer speech-text pairs on Cambodian cultural topics with speaker metadata | only | 727.94 hours; 100K-1M samples | CC-BY-SA-4.0 | open | 2026-06 | Card says manually curated by 12 native speakers; 61 cultural domains; read-style topics. |
| [djsamseng/khmer-speech-large-english-google-translations](https://huggingface.co/datasets/djsamseng/khmer-speech-large-english-google-translations) | Khmer speech with English text generated by Google Translate from Khmer labels | multilingual | 18,000 train + 1,850 test / ~2.6 GB | unknown | open | 2026-03 | English side machine-translated by Google Translate; card notes varied speakers and background noise. |
| [FineWeb-2 (khm_Khmr)](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | Web-crawl pretraining corpus, 1000+ languages; khm_Khmr config | multilingual | khm_Khmr subset unknown (whole dataset >1T tokens) | ODC-By-1.0 | open | 2025-10 | Common Crawl derived, automatically filtered and deduplicated; Khmer-specific filtering quality not verified. |
| [FLEURS (google/fleurs)](https://huggingface.co/datasets/google/fleurs) | Read-speech ASR/LID corpus across 102 languages, parallel to FLORES sentences; km_kh config | multilingual | 102 languages; km_kh subset size unknown | CC-BY-4.0 | open | 2026-05 | Read speech; km_kh config present in card metadata. |
| [jonny122/khmer-newspaper-layout-dataset](https://huggingface.co/datasets/jonny122/khmer-newspaper-layout-dataset) | Khmer newspaper page images with region bounding boxes and masks for layout analysis | only | 9,344 layouts | CC-BY-4.0 | open | 2026-02 | LabelMe JSON annotations on PNG images; newspaper copyright status unverified. (confidence medium: Newspaper source rights unverified.) |
| [Khmer ASR Cultural Dataset (V2), Mozilla Data Collective](https://mozilladatacollective.com/datasets/cml9h5vgc01bxmn075sjeftek) | Khmer speech-text pairs on cultural topics with speaker demographics | only | 106.53 hours / >45,000 recordings / 35.86 GB | CC-BY-SA-4.0 | open | 2026-02 | Attribution to Digital Divide Data required; users agree not to attempt speaker identification. |
| [Khmer News Classification Dataset (sopagnaheang)](https://huggingface.co/datasets/sopagnaheang/Khmer_News_Cls_Dataset) | 6-class Khmer news classification with several preprocessing variants | only | 5,140 train / 661 val / 1,543 test | unknown | open | 2026-07 | Categories: economic, entertainment, life, politics, sports, technology; source of articles not stated in metadata. |
| [KhmerST scene text (GitLab)](https://gitlab.com/vannkinhnom123/khmerst) | Khmer scene-text detection and recognition dataset (ACCV 2024 paper) | only | 1,544 images (997 indoor, 547 outdoor), per paper abstract | unknown | open | 2024-10 | Expert-annotated line-level text with polygon boxes per paper; repo page showed no license. (confidence medium: Size taken from paper search result; repo page showed no license or size.) |
| [khopilot/khmer-lexicon](https://huggingface.co/datasets/khopilot/khmer-lexicon) | Khmer lexicon with semantic and domain metadata for tokenizer training | only | 12,653 unique terms | CC-BY-4.0 | gated | 2025-08 | Auto-gated; card lists royal, government, Buddhist and technical vocabulary; Khmer definitions unverified. |
| [khPOS corpus](https://github.com/ye-kyaw-thu/khPOS) | Khmer part-of-speech tagged corpus for Khmer NLP research | only | unknown | unknown | open | 2024-03 | GitHub license field is null; README license text not read. (confidence medium: Size and any README license statement not checked.) |
| [kimleang123/khmer-text-dataset](https://huggingface.co/datasets/kimleang123/khmer-text-dataset) | Khmer text summarization data combining three public sources | only | 10K-100K rows (card tags) | Apache-2.0 | gated | 2024-11 | Merges KhmerTimes-Summary, LR-Sum and a segmentation-CRF repo; upstream licenses may be stricter. Auto-gated. (confidence medium: Card metadata says Apache 2.0 but sources have their own terms.) |
| [krotreaksmey/khmer-math-textbook](https://huggingface.co/datasets/krotreaksmey/khmer-math-textbook) | Line-level Khmer text and formula images from Cambodian Grade 9-12 math textbooks | only | 29,027 samples / ~410 MB | Apache-2.0 | open | 2026-09 | Extracted from official textbooks; declared Apache 2.0 may not cover the textbook copyright. Flag for human. (confidence medium: Source textbook rights unverified.) |
| [LR-Sum (khm)](https://huggingface.co/datasets/bltlab/lr-sum) | Multilingual news summarization corpus with a Khmer (khm) config | multilingual | ~1 GB stored for all languages; khm subset size unknown | CC-BY-4.0 | open | 2024-12 | News article-summary pairs; khm config confirmed in card metadata. |
| [manhp/khmer-yt-voice-dataset](https://huggingface.co/datasets/manhp/khmer-yt-voice-dataset) | Khmer YouTube audio with speaker-diarization metadata and transcripts | only | 1,033.4 hours across 3,945 videos | CC-BY-SA-4.0 | open | 2026-04 | Extracted from YouTube videos; declared license may not cover source rights; transcript origin (human or ASR) not verified. Flag for human. (confidence medium: Declared license versus YouTube source terms unverified; transcript provenance unclear.) |
| [mC4 / allenai/c4 (km)](https://huggingface.co/datasets/allenai/c4) | Common Crawl text corpus with multilingual variants including a km config | multilingual | unknown | ODC-By-1.0 | open | 2024-01 | Crawled web text with train and validation files; km config confirmed in card metadata. |
| [mrrtmob/khmer_english_ocr_image_line](https://huggingface.co/datasets/mrrtmob/khmer_english_ocr_image_line) | Synthetic Khmer/English text-line images with ground truth for OCR training | multilingual | 12.1M images / 40.2 GB | CC-BY-4.0 | gated | 2026-01 | Synthetic rendered text lines; auto-gated; text source not described in metadata. |
| [mutiyama/alt (HF mirror, alt-km)](https://huggingface.co/datasets/mutiyama/alt) | HF loader for ALT including Khmer parallel subset alt-km | multilingual | unknown | CC-BY-4.0 | open | 2024-01 | Card says cc-by-4.0, while NICT page says the Khmer treebank part is CC BY-NC-SA 4.0; check before use. (confidence medium: Card and upstream license statements differ.) |
| [nanthamom/gemma-english-khmer-translations](https://huggingface.co/datasets/nanthamom/gemma-english-khmer-translations) | English source, ALT reference Khmer and Gemma machine-translated Khmer for 1,000 sentences | multilingual | 1,000 examples / ~985 KB | unknown | open | 2026-09 | Contains machine-translated Khmer (Gemma) next to ALT references; ALT is CC BY-NC-SA for Khmer treebank. |
| [nphearum/khmer-raw-text-3M](https://huggingface.co/datasets/nphearum/khmer-raw-text-3M) | Raw Khmer/English text for LLM pretraining and domain adaptation | only | ~50,000 records / ~3M text segments | MIT | open | 2026-01 | Source of text not stated in metadata; MIT declared without provenance. (confidence medium: Provenance not documented, so declared MIT may not be valid for underlying text.) |
| [OpenSLR SLR42 Khmer TTS data](https://openslr.org/42/) | Multi-speaker studio-style Khmer TTS recordings with transcripts, collected by Google | only | 866 MB (km_kh_male.zip); hours not stated | CC-BY-SA-4.0 | open | 2018 | Page states manual quality review; page lists only the male speaker file. |
| [OPUS-100 (en-km)](https://huggingface.co/datasets/Helsinki-NLP/opus-100) | English-centric parallel corpus, 100 languages; en-km pair | multilingual | 111,483 train / 2,000 val / 2,000 test pairs (en-km) | unknown | open | 2024-02 | Sampled from OPUS, which mixes crawled and subtitle sources; card metadata has no license field. |
| [Panhapich/khmer-text-corpus](https://huggingface.co/datasets/Panhapich/khmer-text-corpus) | Deduplicated Khmer corpus with Khmer/English code-switching, used for tokenizer and diffusion LM training | only | 4.89M sentences / ~7.5 GB | Other | open | 2026-07 | Source not stated in metadata; license is 'Other' without terms text read. (confidence medium: Source and license terms not verified.) |
| [ParaCrawl English-Khmer v2](https://paracrawl.eu/) | Web-mined English-Khmer parallel sentences | multilingual | 1.5M sentences (23M source words) | CC0 (packaging only; underlying text rights not owned) | open | unknown | Automatically mined and aligned from crawled web pages; site has a notice-and-takedown policy. (confidence medium: Date not visible on page; size taken from page summary.) |
| [rinabuoy/khm-asr-open](https://huggingface.co/datasets/rinabuoy/khm-asr-open) | Khmer ASR audio-transcript pairs in parquet | only | 25,538 train + 771 test examples / ~4.8 GB | unknown | open | 2024-10 | Audio provenance and license not stated in card metadata. |
| [SEACrowd khmer_alt_pos](https://huggingface.co/datasets/SEACrowd/khmer_alt_pos) | Manually tokenized and POS-tagged Khmer sentences from ALT | only | 20,000 sentences | CC-BY-NC-SA-4.0 | open | 2024-06 | Human-annotated tokenization and POS tags on ALT news text; non-commercial license. |
| [seanghay/khmer-dictionary-44k](https://huggingface.co/datasets/seanghay/khmer-dictionary-44k) | 44,706 Khmer dictionary entries from the Royal Academy of Cambodia 2022 dictionary | only | 44,706 words / 12 MB | unknown | open | 2024-07 | Card states 'for research purpose only, not for commercial use'; no license field; source is a published dictionary. |
| [seanghay/khmer-hanuman-100k](https://huggingface.co/datasets/seanghay/khmer-hanuman-100k) | 100,001 Khmer text images with text labels for OCR | only | 100,001 examples / ~1.2 GB | unknown | open | 2024-11 | No description or license in metadata; image-text pairs only. (confidence medium: Nature of images (synthetic or real) not documented.) |
| [seanghay/khmer_grkpp_speech](https://huggingface.co/datasets/seanghay/khmer_grkpp_speech) | Force-aligned Khmer speech from Phnom Penh Gendarmerie | only | 533 train examples / 4.446 hours / 1.09 GB | unknown | open | 2023-07 | Author states published for research purposes only; forced-aligned segments. |
| [seanghay/khmer_mpwt_speech](https://huggingface.co/datasets/seanghay/khmer_mpwt_speech) | Khmer speech from a Ministry of Public Works and Transport mobile app, transcribed | only | 2,058 clips / ~1.9 hours / ~27 MB | unknown | open | 2023-06 | Card says imported for research purposes; author notes transcripts may contain errors. |
| [seanghay/km-speech-corpus](https://huggingface.co/datasets/seanghay/km-speech-corpus) | Khmer ASR/TTS speech with transcriptions | only | 14,943 clips / 10.4 hours / 2.3 GB | CC-BY-4.0 | open | 2023-05 | 16 kHz audio, mean 2.5 s per clip; recording provenance not described in metadata. |
| [SeyhaLite Khmer-English translation datasets (collection)](https://huggingface.co/collections/SeyhaLite/datasets-trasnlation-khmer-english) | Domain-split Khmer-English translation sets (travel, legal, medical, IT, etc.), 366k in the combined set | multilingual | 366k pairs combined; per-domain 20k-111k | unknown | open | 2025-02 | Collection page gives no translation method or license; individual dataset cards returned HTTP 401 to me and were not opened. (confidence low: Only the collection page was opened; year of update inferred as 2025 from other context.) |
| [SleukRith Set](https://github.com/donavaly/SleukRith-Set) | Khmer palm-leaf manuscript character dataset | only | unknown | unknown | open | 2019-01 | GitHub license field null; repo has no description; contents not inspected. (confidence low: Only repo metadata opened; contents and size not checked.) |
| [sovannpanhaseng/khmer-pile](https://huggingface.co/datasets/sovannpanhaseng/khmer-pile) | Khmer web corpus re-extracted from FineWeb-2 WARC records with Trafilatura | only | 100K-1M samples | ODC-By-1.0 | open | 2026-09 | Crawled web text; card says boilerplate filtered via Trafilatura; derived from FineWeb-2. |
| [SoyVitou/khmer-handwritten-dataset-4.2k](https://huggingface.co/datasets/SoyVitou/khmer-handwritten-dataset-4.2k) | Khmer handwritten text-line images for OCR | only | 4.2k images / ~88 MB | MIT | open | 2025-03 | Handwriting provenance and annotator process not stated in metadata. |
| [SoyVitou/KhmerSynthetic1M](https://huggingface.co/datasets/SoyVitou/KhmerSynthetic1M) | 1M synthetic Khmer OCR images with labels | only | 1,000,000 images / ~12.7 GB | Apache-2.0 | open | 2026-02 | Synthetic rendered images; text source not described in metadata. |
| [WAT2020 Khmer-English parallel data (ALT + ECCC)](http://lotus.kuee.kyoto-u.ac.jp/WAT/km-en-data/) | Khmer-English MT training data: ALT news plus ECCC court documents | multilingual | 104,660 ECCC + 18,088 ALT train sentences; 1,000 dev; 1,018 test | ECCC-corpus-licence agreement (signed form) for ECCC; citation of Ding et al. 2018 for ALT | request | 2020-07 | ECCC is bilingual legal proceedings text; access requires emailing a signed licence to NICT. |
| [WikiANN (km)](https://huggingface.co/datasets/unimelb-nlp/wikiann) | Silver-standard NER (LOC/PER/ORG, IOB2) for 176 languages including Khmer | multilingual | km: 100 train / 100 validation / 100 test examples | unknown | open | 2024-02 | Automatically derived from Wikipedia link annotations; not manually verified. Card metadata has no license field. |
| [Wikipedia dump (wikimedia/wikipedia 20231101.km)](https://huggingface.co/datasets/wikimedia/wikipedia) | Cleaned Wikipedia articles; Khmer config 20231101.km | multilingual | 11,994 articles / 103.3 MB (km config) | cc-by-sa-3.0, gfdl | open | 2024-01 | Encyclopedic text from a 2023-11-01 dump; Wikipedia markup stripped. |

### Models (32)

| Name | Purpose | Khmer | Size | License | Access | Updated | Notes |
|---|---|---|---|---|---|---|---|
| [Aya-101](https://huggingface.co/CohereLabs/aya-101) | Instruction-tuned multilingual seq2seq LLM covering 101 languages including Khmer | multilingual | 12.9B params | Apache-2.0 | open | 2025-09 | khm in the 101-language list. |
| [BGE-M3](https://huggingface.co/BAAI/bge-m3) | Multilingual dense/sparse embedding model; evaluated on Khmer RAG retrieval in a 2026 paper | multilingual | 567M params (per arXiv 2605.22099) | MIT | open | 2024-07 | Khmer use shown by third-party paper (Hit Rate@3 0.285 on a 200-question set); card metadata does not clearly list Khmer. (confidence medium: Khmer support evidenced by a third-party paper, not the model card.) |
| [Darayut/khmer-text-recognition](https://huggingface.co/Darayut/khmer-text-recognition) | Squeeze-and-Excitation transformer for Khmer text-line recognition | only | ~17.6M params | MIT | open | 2026-09 | Trained on synthetic sets (Darayut document/scene, SoyVitou/KhmerSynthetic1M, khmer-hanuman-100k) per metadata. |
| [facebook/fasttext-km-vectors](https://huggingface.co/facebook/fasttext-km-vectors) | Pretrained fastText word vectors for Khmer | only | ~3 GB | CC-BY-SA-3.0 | open | 2023-06 | Vectors trained on Common Crawl and Wikipedia per fastText project; not verified on this card. (confidence medium: Training-data statement from general fastText knowledge, not this card.) |
| [Gemma-SEA-LION-v3-9B-IT](https://huggingface.co/aisingapore/Gemma-SEA-LION-v3-9B-IT) | Instruction-tuned SEA-LION LLM on Gemma 2 for Southeast Asian languages including Khmer | multilingual | 9.2B params | Gemma | open | 2026-08 | Gemma terms of use apply; Khmer in card language list. |
| [jina-embeddings-v3](https://huggingface.co/jinaai/jina-embeddings-v3) | Multilingual embedding model with km in supported language tags | multilingual | 570M params (per arXiv 2605.22099) | CC-BY-NC-4.0 | open | 2026-04 | Non-commercial license; km appears in card language tags. |
| [khmerttsopensource/khmer-tts](https://huggingface.co/khmerttsopensource/khmer-tts) | Khmer TTS fine-tuned from facebook/mms-tts-khm | only | 83.0M params | CC-BY-NC-4.0 | open | 2026-05 | Fine-tune of a non-commercial base model; training data not stated in metadata. |
| [LaBSE](https://huggingface.co/sentence-transformers/LaBSE) | Language-agnostic sentence embeddings for bitext mining, km in language list | multilingual | unknown | Apache-2.0 | open | 2025-03 | km listed in card languages. |
| [M2M100 1.2B](https://huggingface.co/facebook/m2m100_1.2B) | Many-to-many translation among 100 languages including km | multilingual | 1.2B params (from model name) | MIT | open | 2023-11 | km in card language list. |
| [MADLAD-400 3B MT](https://huggingface.co/google/madlad400-3b-mt) | Multilingual translation model over 400+ languages, km listed | multilingual | 2.94B params | Apache-2.0 | open | 2023-11 | Trained on crawled MADLAD-400 data; km in card language list. |
| [metythorn/khmer-xlm-roberta-base](https://huggingface.co/metythorn/khmer-xlm-roberta-base) | Khmer masked LM based on XLM-RoBERTa | only | ~163M params | Apache-2.0 | open | 2025-07 | Training data not specified in metadata. |
| [MMS-1b-all (khm adapter)](https://huggingface.co/facebook/mms-1b-all) | Wav2Vec2 ASR with per-language adapters for 1,000+ languages incl. khm | multilingual | 1B params | CC-BY-NC-4.0 | open | 2023-06 | Non-commercial; adapter.khm files and vocabs/khm.txt present in repo. |
| [MMS-TTS khm](https://huggingface.co/facebook/mms-tts-khm) | VITS text-to-speech checkpoint for Khmer from Meta MMS | only | 36.3M params | CC-BY-NC-4.0 | open | 2023-09 | Non-commercial license. |
| [mT5-base](https://huggingface.co/google/mt5-base) | Multilingual T5 pretrained on mC4 across 101 languages including km | multilingual | unknown (params not in metadata) | Apache-2.0 | open | 2023-01 | Pretrained only, no supervised fine-tuning; km in language list. |
| [multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) | Multilingual text embedding model with km among language tags | multilingual | unknown (params not in metadata) | MIT | open | 2026-04 | km in card language tags; no Khmer-specific evaluation seen. |
| [NLLB-200 3.3B](https://huggingface.co/facebook/nllb-200-3.3B) | Many-to-many translation model covering 200 languages including khm_Khmr | multilingual | 3.3B params | CC-BY-NC-4.0 | open | 2023-02 | Non-commercial license; khm_Khmr in language list. |
| [nphearum/Qwen3.5-4B-khmer-delta](https://huggingface.co/nphearum/Qwen3.5-4B-khmer-delta) | Community Khmer/English QA fine-tune of Qwen3.5-4B | multilingual | ~4.7B params | MIT | open | 2026-03 | Trained on nphearum/khmer-raw-text-3M and nphearum/gsm678-thinking; no evaluation seen; base-model license not checked. (confidence medium: Metadata only; no model card evaluation or Khmer quality evidence.) |
| [Omnilingual ASR (omniASR-LLM-7B)](https://huggingface.co/facebook/omniASR-LLM-7B) | Meta open ASR for 1,600+ languages; khm_Khmr appears in language ID list | multilingual | 7B params class (~31.2 GB) | Apache-2.0 | open | 2025-11 | khm_Khmr found in repo lang_ids.py; per-language Khmer accuracy not checked. GitHub repo license shows NOASSERTION. (confidence medium: Khmer inclusion from code list; Khmer accuracy and repo license not verified.) |
| [PrahokBART](https://huggingface.co/prajdabre/prahokbart) | Compact seq2seq pretrained on Khmer and English for MT, summarization, headline generation (COLING 2025) | multilingual | base ~61.6M params (nict-astrec-att/prahokbart_base); big variant also exists | MIT | open | 2025-04 | Trained on curated Khmer and English corpora with word segmentation and normalization modules, per paper; needs those preprocessing steps. |
| [Qwen-SEA-LION-v4-32B-IT](https://huggingface.co/aisingapore/Qwen-SEA-LION-v4-32B-IT) | Instruction-tuned SEA-LION v4 LLM on Qwen for Southeast Asian languages including Khmer | multilingual | 32.76B params | MIT | open | 2026-08 | Khmer listed in supported languages; upstream base model terms not checked. |
| [Sailor2-8B-Chat](https://huggingface.co/sail/Sailor2-8B-Chat) | Chat LLM for Southeast Asian languages including Khmer | multilingual | 8.5B params | Apache-2.0 | open | 2025-02 | Khmer in card's language list; base model sail/Sailor2-8B also lists km. |
| [SeaLLMs-v3-7B-Chat](https://huggingface.co/SeaLLMs/SeaLLMs-v3-7B-Chat) | Chat LLM for Southeast Asian languages including Khmer | multilingual | 7.6B params | other (license_name: seallms) | open | 2024-09 | Custom license 'seallms'; terms text not read. Khmer in card language list. |
| [seanghay/khmer-pos-roberta](https://huggingface.co/seanghay/khmer-pos-roberta) | XLM-RoBERTa token classifier for Khmer POS tagging | only | 277.5M params | Apache-2.0 | open | 2023-07 | Trained on seanghay/khPOS per metadata; upstream khPOS license unknown. |
| [seanghay/Qwen3-ASR-0.6B-Khmer](https://huggingface.co/seanghay/Qwen3-ASR-0.6B-Khmer) | Khmer ASR fine-tune of Qwen3-ASR-0.6B | only | ~0.6B params (782 MB BF16) | Apache-2.0 | open | 2026-07 | Trained on DDD-Cambodia/khmer-speech-dataset per metadata. |
| [seanghay/w2v-bert-2.0-khmer](https://huggingface.co/seanghay/w2v-bert-2.0-khmer) | W2v-BERT 2.0 fine-tuned for Khmer ASR | only | 605.76M params | MIT | open | 2024-07 | Fine-tuned on OpenSLR data per metadata. |
| [seanghay/whisper-small-khmer-v2](https://huggingface.co/seanghay/whisper-small-khmer-v2) | Whisper-small fine-tuned for Khmer ASR | only | 241.7M params | Apache-2.0 | open | 2025-01 | Trained on OpenSLR, FLEURS Khmer and km-speech-corpus per metadata. |
| [seanghay/xlm-roberta-khmer-small](https://huggingface.co/seanghay/xlm-roberta-khmer-small) | Small XLM-RoBERTa masked LM for Khmer | only | 49.7M params | Apache-2.0 | open | 2024-07 | Training data not specified in metadata. |
| [songhieng/khmer-mt5-summarization](https://huggingface.co/songhieng/khmer-mt5-summarization) | mT5-small fine-tuned for Khmer summarization | only | 300.2M params | MIT | open | 2025-02 | Trained on kimleang123/khmer-text-dataset; MIT may conflict with upstream source terms. |
| [sumnim/VoxCPM2-Khmer](https://huggingface.co/sumnim/VoxCPM2-Khmer) | Khmer text-to-speech model built on VoxCPM2 | only | 2.29B params | Apache-2.0 | open | 2026-05 | Base model and training data not stated in metadata. (confidence medium: Training data and base model undocumented in metadata I read.) |
| [vitouphy/wav2vec2-xls-r-300m-khmer](https://huggingface.co/vitouphy/wav2vec2-xls-r-300m-khmer) | XLS-R 300M fine-tuned for Khmer ASR | only | 315.5M params | Apache-2.0 | open | 2023-05 | Trained on OpenSLR Khmer plus Robust Speech Event community data per metadata. |
| [Whisper large-v3](https://huggingface.co/openai/whisper-large-v3) | Multilingual ASR/translation model; Khmer (km) in supported language list | multilingual | 1.54B params | Apache-2.0 | open | 2024-08 | km in language list; no Khmer WER checked by me. |
| [XLM-RoBERTa base](https://huggingface.co/FacebookAI/xlm-roberta-base) | Multilingual masked LM over 100 languages including km | multilingual | 278.9M params | MIT | open | 2024-02 | Pretrained on CC-100; km in language list. |

### Tools (17)

| Name | Purpose | Khmer | Size | License | Access | Updated | Notes |
|---|---|---|---|---|---|---|---|
| [GlotLID (cis-lmu/glotlid)](https://huggingface.co/cis-lmu/glotlid) | fastText language identification including khm | multilingual | ~8.2 GB repo | Apache-2.0 | open | 2024-04 | khm listed among supported codes; card says license comes with notices. |
| [ICU Khmer dictionary (khmerdict.txt)](https://github.com/unicode-org/icu/blob/main/icu4c/source/data/brkitr/dictionaries/khmerdict.txt) | Word list used by ICU dictionary-based break iterator for Khmer | only | 2,031,114 bytes | Unicode-3.0 | open | 2026-09 | File presence and size confirmed via contents API; repo license text not read. (confidence medium: Exact ICU license text and file-level history not checked.) |
| [khmer-nltk](https://github.com/VietHoang1512/khmer-nltk) | Khmer NLP toolkit: sentence/word segmentation, POS tagging, NER, text classification | only | unknown | Apache-2.0 | open | 2026-03 | Published on PyPI as khmer-nltk; training data not specified on repo page. |
| [Khmerlang-Keyboard](https://github.com/khmerlang/Khmerlang-Keyboard) | Mobile Khmer keyboard with local word segmentation | only | unknown | GPL-3.0 | open | 2026-08 | GPL-3.0 copyleft; platform details not checked. |
| [khopilot/km-tokenizer-khmer](https://huggingface.co/khopilot/km-tokenizer-khmer) | SentencePiece tokenizer for Khmer, trained on multi-domain Khmer text | only | unknown (vocab size not stated) | Apache-2.0 | gated | 2026-03 | Manual-approval gating; training corpus described as news, literature, technical, social media and religious text. |
| [Kiri OCR](https://github.com/mrrtmob/kiri-ocr) | Lightweight OCR library for English and Khmer documents | multilingual | ~736 MB model on HF (mrrtmob/kiri-ocr) | Apache-2.0 | open | 2026-02 | Khmer and English only; 40 stars; accuracy not verified. |
| [phylypo/segmentation-crf-khmer](https://github.com/phylypo/segmentation-crf-khmer) | CRF word segmentation for Khmer documents | only | unknown | unknown | open | 2025-10 | GitHub license field null; training corpus not checked. (confidence medium: Only repo metadata opened.) |
| [seanghay/khmer-neural-segmenter](https://github.com/seanghay/khmer-neural-segmenter) | Neural Khmer word segmenter | only | unknown | MIT | open | 2026-02 | Training data and accuracy not checked. (confidence medium: Only repo metadata opened.) |
| [seanghay/khmer-unicode-converter](https://github.com/seanghay/khmer-unicode-converter) | JavaScript converter from legacy Khmer font encodings to Unicode | only | unknown | LGPL-2.1 | open | 2026-07 | Conversion tables not verified; 0 stars. (confidence medium: Only repo metadata opened.) |
| [seanghay/khmercut](https://github.com/seanghay/khmercut) | Fast Khmer word segmentation with optional neural model and sub-word splitting | only | unknown | unknown | open | 2026-08 | GitHub license field is null; pip package khmercut per README. (confidence medium: No license in API; LICENSE file or PyPI metadata not checked.) |
| [seanghay/khmernormalizer](https://github.com/seanghay/khmernormalizer) | Toolkit for Khmer NLP preprocessing and normalization | only | unknown | MIT | open | 2026-04 | Description reads 'A missing toolkit for Khmer Natural Language Processing'; rule sources not checked. (confidence medium: Functionality not inspected beyond repo description.) |
| [seanghay/khmertagger](https://github.com/seanghay/khmertagger) | Inverse text normalization for Khmer ASR output | only | unknown | Apache-2.0 | open | 2025-09 | Model and data details not inspected. (confidence medium: Only repo metadata opened.) |
| [sillsdev/khmer-character-specification](https://github.com/sillsdev/khmer-character-specification) | SIL machine-readable Khmer character and syllable structure specification | only | unknown | unknown | open | 2025-03 | GitHub license field is null; repo LICENSE file not looked for separately. (confidence medium: Only API metadata checked; a license file may exist.) |
| [sillsdev/khmer-normalizer](https://github.com/sillsdev/khmer-normalizer) | Normalizes Khmer strings per Unicode guidance (UTN #61); Modern and Middle Khmer | only | unknown | MIT | open | 2024-08 | TypeScript with CLI; GitHub API reports NOASSERTION but LICENSE.md text is MIT (Copyright SIL International). |
| [Sovichea/khmer_segmenter](https://github.com/Sovichea/khmer_segmenter) | Zero-dependency Viterbi Khmer word segmenter for low-memory edge deployment | only | unknown | MIT | open | 2026-09 | Dictionary-based; accuracy claims not verified by me. |
| [Tesseract khm.traineddata](https://github.com/tesseract-ocr/tessdata/blob/main/khm.traineddata) | Tesseract LSTM/legacy OCR model for Khmer | only | 1,446,906 bytes | Apache-2.0 | open | 2024-03 | License is repo-level; per-file training-data terms not checked. (confidence medium: License seen only at repo level.) |
| [Trey314159/KhmerSyllableReordering](https://github.com/Trey314159/KhmerSyllableReordering) | Reorders Khmer syllable characters for search indexing | only | unknown | MIT | open | 2021-09 | Reordering rules not reviewed here; needs Khmer/Unicode source check by human. |
<!-- tables:end -->
