# What Khmer costs in tokens (September 2026)

*Samputhy Khim* · **Status:** draft for review · Data:
[`data/tokenizers-ntrex.json`](data/tokenizers-ntrex.json)

Language models read text as tokens, and they are priced, limited and trained in tokens.
If a tokenizer splits Khmer into many more pieces than English, the same content costs
more, fits less into a context window, and gets less training signal per sentence. This
report measures that gap for widely used public tokenizers, and checks whether
normalizing the Khmer text first changes it.

## Method

- **Text.** NTREX-128 (Microsoft, CC BY-SA 4.0): 1,997 English news sentences and their
  professional Khmer translations. Because both sides say the same thing, the ratio of
  token counts measures how much more Khmer costs. This ratio is the "tokenization
  parity" of [Petrov et al. (2023)](https://arxiv.org/abs/2305.15425); 1.0 means Khmer
  costs the same as English.
- **Tokenizers.** Eleven, from tokenizer files only (no model weights): OpenAI's
  `cl100k_base` and `o200k_base` via `tiktoken`, and the published tokenizers of Qwen2.5,
  DeepSeek-V3, Sailor2, SEA-LION v3 (Gemma 2), BLOOM, XLM-RoBERTa, mT5 and NLLB-200.
  Counts exclude special tokens. A one-token-per-character "tokenizer" is included as a
  baseline.
- **Units.** Khmer is written without spaces between words, so Khmer counts are given
  per character and per syllable (a syllable cluster as defined in the Pheasa
  normalization spec). English counts are per whitespace-separated word.
- **Normalization.** Every Khmer sentence was also tokenized after
  `pheasa.normalize` (normalization version 1).

To reproduce (the JSON file lists every tokenizer used):

```bash
uv sync --group research
uv run python scripts/fetch_sources.py ntrex tokenizers
uv run python scripts/tokenizer_stats.py \
  --km data/raw/ntrex/newstest2019-ref.khm.txt --en data/raw/ntrex/newstest2019-src.eng.txt \
  --tokenizer chars --tokenizer tiktoken:o200k_base --tokenizer tiktoken:cl100k_base \
  --tokenizer hf:Qwen/Qwen2.5-7B-Instruct --tokenizer hf:deepseek-ai/DeepSeek-V3 \
  --tokenizer hf:sail/Sailor2-8B-Chat --tokenizer hf:aisingapore/Gemma-SEA-LION-v3-9B-IT \
  --tokenizer hf:FacebookAI/xlm-roberta-base --tokenizer hf:bigscience/bloom \
  --tokenizer spm:data/raw/tokenizers/mt5-base-spiece.model \
  --tokenizer spm:data/raw/tokenizers/nllb-200-distilled-600M-sentencepiece.bpe.model \
  --json reports/data/tokenizers-ntrex.json
```

## Results

| Tokenizer | Khmer tokens per character | Khmer tokens per syllable | English tokens per word | Khmer ÷ English tokens | Change on normalized sentences |
|---|---|---|---|---|---|
| OpenAI cl100k_base (GPT-4, GPT-3.5) | 1.54 | 3.37 | 1.24 | 8.50 | -0.2% |
| DeepSeek-V3 | 1.18 | 2.58 | 1.25 | 6.46 | -0.2% |
| Qwen2.5 | 1.15 | 2.53 | 1.26 | 6.27 | -0.1% |
| Sailor2 (SEA) | 1.15 | 2.53 | 1.26 | 6.27 | -0.1% |
| BLOOM | 1.10 | 2.41 | 1.26 | 5.97 | -0.1% |
| Gemma 2 (via SEA-LION v3) | 0.92 | 2.02 | 1.26 | 5.03 | +0.0% |
| OpenAI o200k_base (GPT-4o family) | 0.58 | 1.27 | 1.23 | 3.24 | -0.9% |
| NLLB-200 | 0.36 | 0.78 | 1.41 | 1.73 | -1.4% |
| XLM-RoBERTa | 0.31 | 0.67 | 1.41 | 1.49 | -2.2% |
| mT5 | 0.30 | 0.65 | 1.55 | 1.31 | -2.3% |
| Characters (baseline) | 1.00 | 2.19 | 5.89 | 1.16 | +0.0% |

"Change on normalized sentences" is the change in Khmer token count, for the 140
sentences (7%) that normalization changed, when the normalized form is tokenized
instead of the original.

## Findings

1. **Khmer costs 3 to 8.5 times as many tokens as English in LLM tokenizers.** The
   GPT-4 tokenizer (`cl100k_base`) uses 1.54 tokens per Khmer character, more than one
   token per letter, and 8.5 times the English count for the same sentences. The
   GPT-4o tokenizer (`o200k_base`) reduces this to 3.2 times. The open LLM tokenizers
   tested sit between 5 and 6.5 times.
2. **A regional model does not mean a Khmer-efficient tokenizer.** Sailor2, a Southeast
   Asian model, gives exactly the same counts as Qwen2.5 on every sentence, consistent
   with it reusing Qwen2.5's tokenizer. SEA-LION v3 uses Gemma 2's tokenizer (5.0
   times).
3. **Multilingual encoder and translation tokenizers are near parity.** mT5, XLM-RoBERTa
   and NLLB-200 spend 1.3 to 1.7 times the English count: their vocabularies were built
   with many languages in mind.
4. **Normalization never made Khmer more expensive here, and sometimes cheaper.**
   Normalization changed 140 of the 1,997 Khmer sentences (subscript order in 59, coeng
   da in 55, mark order in 33, one -u). On those sentences the normalized text needed
   up to 2.3% fewer tokens (mT5, XLM-RoBERTa) and never more. A likely reason is that
   the canonical forms are the more frequent ones in the text these tokenizers were
   trained on; this was not tested. The size of the effect is small because professional
   translations are mostly well formed: in a sample of Khmer Wikipedia, one sentence in
   eight needs normalization, against one in fourteen here.

The practical point of normalization is consistency rather than token savings: the
same word always becomes the same tokens, so a model does not have to learn several
spellings of one word.

## Limits

- One test set, news domain, professionally translated. Informal and web text will
  differ.
- The ratio depends on the translations: a Khmer translation that is longer or shorter
  in content shifts it. Averaging over 1,997 sentences limits but does not remove this.
- Token counts say nothing about how well a model understands Khmer.
- Tokenizers of proprietary models other than OpenAI's are not public and were not
  measured. Gated tokenizers (Llama, Gemma 3) were not included.
