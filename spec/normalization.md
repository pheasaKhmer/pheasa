# Pheasa Khmer normalization specification

**Status:** draft for `NORMALIZATION_VERSION = "1"` (targets pheasa v0.1)
**Unicode version:** 18.0.0 (see D-006)
**Scope:** Modern Khmer (`km`). Middle Khmer (`xhm`) is out of scope for version 1.

## Goal

Make Khmer text that renders identically also compare identically, without changing
how it looks or reads. Pheasa does not correct spelling. When it finds something it
cannot safely fix, it leaves the text alone and flags it.

## Normative sources

In priority order. Every rule below cites one of these.

| Key | Source | Notes |
|---|---|---|
| **TUS** | The Unicode Standard 18.0.0, §16.4 Khmer; §23 Specials | The core spec. §16.4 refers implementers to UTN #61. |
| **UCD** | Unicode Character Database 18.0.0 | Khmer entries (U+1780–17FF, U+19E0–19FF) are byte-identical to 15.1.0. |
| **UTN61** | Unicode Technical Note #61, *Khmer Encoding Structure*, M. Hosken, February 2025 (V2) | Defines the syllable structure and normalization this spec follows (D-005). Page numbers below refer to this PDF. |
| **SIL** | `khnormal`, SIL Global, MIT license, `sillsdev/khmer-character-specification` at commit `08ae0374` | The reference implementation of UTN61. Pheasa uses it as a test oracle (D-007). |
| **UAX15** | Unicode Standard Annex #15, *Unicode Normalization Forms* | NFC |

UTN61 is a technical note, not part of the standard. Where it disagrees with TUS, this
spec follows UTN61 and records the conflict (see Conflicts).

## Pipeline

`normalize(text, **options)` runs these stages. Stages 2 and 3 are the UTN61 core and
must match the SIL oracle. Stages 1 and 4 are Pheasa's own policy.

Execution order is 1.1, Stage 4, 1.3 (NFC), Stage 2, Stage 3. Stage 4 is numbered last
because it is optional, but it runs before NFC and before clustering. Removing a ZWSP or
U+17B4 can join a coeng to the next base or expose `<17DD 17D2>` to NFC, so running the
options last would give output that changes when normalized again.

```
1. pre-clean   BOM, NFC                            (Pheasa policy)
2. reorder     sort each syllable cluster          (UTN61)
3. fold        do-not-use sequences -> preferred   (UTN61)
4. options     ZWSP, digits, deprecated chars      (Pheasa policy, opt-in)
5. validate    flag non-conformant syllables       (UTN61 p. 16; never modifies text)
```

---

## Stage 1: pre-clean

| # | Rule | Default | Source |
|---|---|---|---|
| 1.1 | Remove U+FEFF at the start of the text. A run of them (for example from concatenated files) is removed as a whole, so that normalizing twice gives the same result. | on | TUS §23.8. Since Unicode 3.2, U+FEFF is used only as a byte order mark and not as a zero-width no-break space. |
| 1.2 | U+FEFF elsewhere is preserved and flagged. | on | Same as 1.1. Mid-text use is ambiguous, so it is not silently removed. |
| 1.3 | Apply NFC. | on | UAX15. For Khmer text NFC is nearly a no-op: no Khmer character decomposes, and only U+17D2 (ccc=9) and U+17DD (ccc=230) have a non-zero combining class (UCD; UTN61 p. 27). NFC runs for the benefit of non-Khmer text in mixed strings. |

NFC uses the interpreter's `unicodedata`. For Khmer text the result is the same on every
supported Python, because the Khmer combining classes have not changed since they were
assigned. Non-Khmer characters assigned after the interpreter's Unicode version are
treated as unassigned by NFC, so mixed text containing them can normalize differently on
older Pythons.

NFC moves U+17D2 in front of a directly preceding U+17DD. In `1780 17DD 17D2 179A` this
detaches the subscript: the result is `1780 17D2 17DD 179A`, where 179A starts a new
cluster. The oracle, run on NFC input as the differential test requires, does the same.

**Invariant:** `NFC(normalize(x)) == normalize(x)`. Pheasa output must survive a
downstream NFC unchanged. UTN61 pp. 27–28 notes that NFC reorders `<17DD 17D2>` to
`<17D2 17DD>`. Under UTN61's structure, a coeng after ATTHACAN is a final coeng, which
is Middle Khmer only and always marked with ZWJ. ZWJ has ccc=0, so it blocks the
reorder. Property tests must confirm this.

## Stage 2: reorder syllable clusters

**2.1 Clusters.** A cluster starts at a base character: a consonant U+1780–17A2 or an
independent vowel U+17A5–17B3 (UTN61 p. 16). A base directly after U+17D2 COENG or
U+200D ZWJ does not start a cluster: it is part of the subscript or final coeng that
the joiner opens, and takes the joiner's category. The same holds for a COENG directly
after a joiner. The cluster continues through every following character whose category
is 2 to 12 below, and ends before the next base or Other character. U+25CC DOTTED
CIRCLE is in SIL's `B` pattern, which validation and Stage 3 use, but it is Other here
and does not start a cluster (it matches the oracle's `charcat`).

**2.2 Sort.** Characters within a cluster are stably sorted by category, so typed order
is kept inside each category. A subscript (COENG + base) stays together because both
characters share a category and were adjacent.

**2.3 Stability guard.** A cluster is left exactly as typed, and flagged, if its sorted
form would change the text around it:

- the sorted form ends in COENG or ZWJ and the next character is a base. This happens
  only when the cluster holds a dangling COENG or a stray ZWJ. Emitting it would turn
  the next syllable's base into a subscript, and normalizing again would sort the joined
  cluster differently;
- the sorted form ends in a character whose combining class is higher than that of the
  next character, and the next character's class is not 0. NFC would then reorder the
  two, breaking the NFC invariant. This needs a non-Khmer combining mark after the
  cluster, such as `1780 17DD 17B6 0316`.

Either case means the input is malformed, so the conservative choice (see Goal) is to
leave it unchanged. The oracle sorts these clusters anyway; see Differences from the
oracle and D-010.

| Order | Category | Code points | Source |
|---|---|---|---|
| 1 | Base | 1780–17A2, 17A5–17B3 | UTN61 p. 16 |
| 2 | Robat | 17CC | UTN61 p. 16 |
| 3 | Coeng (17D2 + base, treated as one unit) | 17D2 followed by 1780–17A2 or 17A5–17B3 | UTN61 p. 16 |
| 4 | Shifter | 17C9, 17CA | UTN61 pp. 16, 25. See Conflict C1. |
| 5 | ZWNJ | 200C | UTN61 p. 16 (`17CA ZWNJ`, `17C9 ZWNJ`) |
| 6 | Vowel, pre-base or split | 17BE–17C5 | SIL categories |
| 7 | Vowel, below | 17BB–17BD | SIL categories |
| 8 | Vowel, above | 17B7–17BA | SIL categories |
| 9 | Vowel, post-base | 17B6 | SIL categories |
| 10 | Modifier signs | 17C6, 17CB, 17CD–17D1, 17DD (+17D3, see C3) | UTN61 p. 16; SIL |
| 11 | Final | 17C7, 17C8 | UTN61 p. 16 |
| 12 | Final coeng: ZWJ, and every COENG or base chained after it | 200D | UTN61 pp. 14–15 (Middle Khmer final coeng, marked with ZWJ); SIL `ZFCoeng` |

The following are **Other**. They end a cluster and are never moved: 17A3, 17A4, 17B4,
17B5, 17D4–17DC, and everything outside U+1780–17DD except ZWNJ and ZWJ (UTN61 p. 13;
SIL `categories`). U+17D3 is Other in UTN61 (pp. 13, 16) but a modifier in SIL's
`categories` and `MS` pattern. Pheasa follows the oracle, because U+17D3 is discouraged
(Identifier_Type=Obsolete, UTN61 p. 27) and rare. Any occurrence is flagged. See C3.

Example (README): `1781 17C2 17D2 1798 179A` → `1781 17D2 1798 17C2 179A`, that is
ខែ្មរ → ខ្មែរ.

## Stage 3: fold do-not-use sequences

These apply within a cluster, after sorting, in this order. Every one replaces a sequence
with another that renders identically (UTN61 pp. 28–29, "Do not use" table).

| # | From | To | Source |
|---|---|---|---|
| 3.1 | `(ZWJ)? 17D2` followed by one or more of {17D2, 200C, 200D} | the first `(ZWJ)? 17D2` alone | SIL: removes repeated invisible characters after a coeng |
| 3.2 | `17BE 17B6` | `17C4 17B8` | UTN61 p. 29 (visually indistinct) |
| 3.3 | `17C1 (17BB–17BD)? 17B8` | `17BE (…)` | UTN61 p. 28 (split vowel) |
| 3.4 | `17C1 (17BB–17BD)? 17B6` | `17C4 (…)` | UTN61 p. 28 (split vowel) |
| 3.5 | `17BE 17BB` | `17BB 17BE` | SIL (sets up 3.6) |
| 3.6 | -u (17BB) directly after the consonant cluster (and an optional pre-base vowel), before an above vowel or 17D0 | 17CA after a STRONG cluster, 17C9 after a WEAK one, placed before the pre-base vowel. See "Rule 3.6 in detail". | UTN61 pp. 16–17, 22–25, 28–30 |
| 3.7 | `17D2 179A 17D2 X` (coeng ro first) | `17D2 X 17D2 179A`, repeated until no coeng ro precedes another coeng | UTN61 pp. 16, 29, 35 |
| 3.8 | `17D2 178A` (coeng da) | `17D2 178F` (coeng ta) | UTN61 pp. 31–32; default confirmed by native-speaker review (D-008). Option `preserve_coeng_da=True` disables it. |
| 3.9 | — | Repeat Stage 2 and rules 3.1–3.8 on the cluster until it stops changing. Rule 2.3 then applies to the result. | Pheasa (idempotence). A fold can leave the cluster unsorted or expose another fold, e.g. `1798 17BB 17BE 17BB`. The loop ends: every round either shortens the cluster, removes a -u, 17BE or coeng da, or only permutes it, and the round after a permutation-only round changes nothing. |

### Rule 3.6 in detail

The consonant cluster is `Base Robat? (17D2 Base)*` at the start of the sorted cluster
(UTN61 p. 16). Rule 3.6 applies only if the -u follows it directly, or with one pre-base
vowel 17C1–17C5 in between (UTN61 p. 18, Middle Khmer AboveVowel). Anything else in
between, such as a shifter, ZWNJ or a second robat, means the rule does not apply.

- **STRONG** (UTN61 p. 17 prose, p. 22 rules 1–3): the consonant cluster contains a
  StrongBase consonant `1780–1783 1785–1788 178A–178D 178F–1792 1795–1797 179E–17A0 17A2`
  (UTN61 pp. 16, 23) and no BA (1794). Otherwise it is **WEAK**. Independent vowels are
  weak (UTN61 p. 24).
- UTN61 p. 16 also gives STRONG as the regex `StrongContext`, used as a lookbehind, so
  it can match a suffix of the cluster. Pheasa evaluates that regex too, with NonBA
  widened to include independent vowels (UTN61 p. 24; SIL). If the prose and the regex
  disagree, the -u is left alone and flagged (conflict C4).
- STRONG: -u becomes 17CA if the next character is an AboveVowel `17B7–17BA 17BE 17DD`
  or `17B6 17C6` (UTN61 p. 16). Not before 17D0, because samyok sannya does not push
  triisap down (UTN61 p. 25).
- WEAK: -u becomes 17C9 before an AboveVowel, or before 17D0 when the pre-base vowel,
  if any, is 17C1–17C3 (UTN61 p. 16, AboveVowelSamyok).

**Not done in version 1:** UTN61 p. 35 says legacy "digit + coeng + khan" lunar-date
sequences should become U+19E0–19FF symbols. SIL's `khnormal` contains that
substitution, but it never runs: digits are Other, so they are never inside a cluster.
Pheasa version 1 matches the oracle's actual behavior (no conversion) and flags these
sequences. See D-009.

## Stage 4: options (Pheasa policy)

Everything here is outside UTN61's scope. Anything that removes or rewrites visible
information is off by default. Each option is a per-character substitution applied
after rule 1.1 and before rule 1.3 (see Pipeline). An unknown option value raises
`ValueError`.

| Option | Default | Behavior | Source |
|---|---|---|---|
| `zwsp` | `"keep"` | `"keep"`, `"strip"`, or `"space"` for U+200B | TUS §16.4: ZWSP is the recommended way to mark Khmer word boundaries, so keeping it is the default. |
| `digits` | `"keep"` | `"keep"`, `"khmer"`, or `"ascii"`. Maps only U+17E0–17E9 ↔ U+0030–0039. | UCD: 17E0–17E9 are gc=Nd with decimal values 0–9. U+17F0–17F9 (LEK ATTAK) are gc=No divination numerals and are **never** converted. |
| `fold_deprecated` | `False` | 17A3→17A2; 17A4→17A2 17B6; 17D8→17D4 179B 17D4; remove 17B4 and 17B5 | UTN61 pp. 27, 30 (intentional confusables); TUS §16.4 (17A3 and 17A4 deprecated; 17B4 and 17B5 "should be considered errors"; 17D8 discouraged) |

ZWNJ and ZWJ are never removed, except as part of rule 3.1. UTN61 gives them roles:
ZWNJ after a shifter keeps it from downshifting (p. 16), and ZWJ marks a final coeng in
Middle Khmer (pp. 14–15). Occurrences anywhere else are flagged, not removed.

## Validation (report only)

Validation never modifies text. `pheasa.validate(text)` returns the issues in any text.
`normalize(text, report=True)` returns a `Report` with:

- `text`: the normalized text, identical to `normalize(text)` with the same options;
- `changes`: one `Change` per edited span, in input order. Each has `start` and `end`
  (offsets into the input), `before` (the input span), `after`, `output_start` (where
  `after` begins in the output) and `rules`, the IDs of every rule that contributed:
  `1.1`, `1.3`, `2.2`, `3.1`–`3.9`, `4.zwsp`, `4.digits`, `4.deprecated`. Splicing every
  `after` into the input rebuilds the output exactly. NFC is tracked by splitting the
  text only where NFC cannot act across the split (UAX15: the next character must
  decompose to a starter and must not compose with what precedes it);
- `issues`: `validate(text)` of the output, plus V9.

Issues use these codes, with offsets into the validated text:

| Code | Issue | Source |
|---|---|---|
| V1 | Dangling coeng: 17D2 not followed by a base | UTN61 p. 16 (Coengs) |
| V2 | ZWNJ other than directly after a shifter that would otherwise downshift | UTN61 p. 16 (Shifter); C2 |
| V3 | ZWJ next to Khmer text. `ZWJ 17D2 base` is reported as a final coeng, which UTN61 allows only in Middle Khmer | UTN61 pp. 14–16 |
| V4 | A mark that does not fit the syllable: a second vowel (including `17C4 17B8` from rule 3.2), a third modifier, 17D0 or 17DD after -u, a third coeng, a misplaced shifter or robat. A -u before an above vowel that rule 3.6 left alone (O6, O7) is reported here | UTN61 p. 16 |
| V5 | A mark with no base before it | UTN61 p. 16 |
| V6 | Legacy lunar-date sequence: digit + 17D2 + 17D4, or 17D4 + 17D2 + digit or 17D4 | UTN61 p. 35; D-009 |
| V7 | U+17D3 (discouraged) | UTN61 p. 27; C3 |
| V8 | U+FEFF after the start of the text | Rule 1.2 |
| V9 | Cluster left as typed by rule 2.3 (report only) | Rule 2.3 |

The syllable check follows the UTN61 p. 16 Modern Khmer grammar. It also accepts U+17D3
as a modifier (C3), and accepts U+25CC DOTTED CIRCLE as a base or after a coeng so that
a mark shown in isolation is not flagged (SIL `khtest` pattern `B`). Stage 2 still treats U+25CC as
Other, as the oracle's sort does.

**Differences from SIL `khtest`.** Anything `khtest` rejects, Pheasa flags. Pheasa is
stricter in one respect: `khtest` accepts every character outside U+1780–17D2 as a
standalone syllable, including U+17DD, ZWNJ and ZWJ. UTN61 p. 16 lists only
`17A3 17A4 17B4 17B5 17D3–17DC` as Other, so Pheasa flags a lone 17DD (V4 or V5) and a
stray ZWNJ or ZWJ (V2, V3). ZWJ in non-Khmer text, such as an emoji sequence, is not
flagged.

## Conflicts between sources

**C1. Where the shifter goes.** TUS 18.0 §16.4 says a consonant shifter "should always
be encoded immediately following the base consonant" (before any coeng). UTN61 pp. 13,
25–26 puts it after the coengs, for three reasons: collation tailoring, a single fixed
position, and the fact that the shifter applies to the cluster's series as a whole.
UTN61 p. 34 reports that the HarfBuzz and Microsoft shapers accept the shifter after the
coengs.

**Resolution:** follow UTN61 (D-005). TUS §16.4 itself points implementers to UTN61, and
the oracle follows it.

**Consequence:** text typed the way TUS recommends will be reordered. For example,
`1798 17C9 17D2 1784 17C3` becomes `1798 17D2 1784 17C9 17C3`.

**Rendering check (Phase 1b):** `scripts/check_shifter_rendering.py` shapes both orders
with HarfBuzz for every consonant × shifter × subscript × vowel and compares the glyphs
drawn (ID and position, ignoring the emission order of zero-width marks). First result,
2026-09-30, HarfBuzz 14.5.0 via uharfbuzz 0.56.2, with the two Khmer fonts that ship with
macOS (Khmer Sangam MN, Khmer MN): about 75% of the 49,000 pairs draw differently, and
about 97% of those with a vowel. Many of these differences are different glyph variants
that may look the same. Some appear to be visibly different, such as `1798 17C9 17D2
179B 17B6` against `1798 17D2 179B 17C9 17B6`. Apple's fonts target Core Text rather than
HarfBuzz, so this is not yet evidence about the fonts most used in Cambodia.
Native-speaker review of these renderings (Q-009, 2026-09-30) found the UTN61-order
column mostly correct and the TUS-order renderings wrong. This supports the resolution
above: in these fonts, reordering fixes rendering rather than changing it. The check
still has to be repeated with Noto Sans Khmer and Khmer OS.

**C2. ZWNJ position.** The TUS §16.4 grammar allows ZWNJ or ZWJ before a dependent vowel
(`{Z} V`). UTN61 allows ZWNJ only after a shifter. **Resolution:** preserve and flag,
never remove.

**C3. U+17D3.** UTN61 treats it as Other; SIL's code treats it as a modifier. **Resolution:** follow the oracle and flag it (see Stage 2).

**C4. STRONG: prose versus regex.** UTN61 pp. 17 and 22 say a cluster that contains BA
is weak, whatever else it contains. The `StrongContext` regex on p. 16 is used as a
lookbehind, so it matches any suffix of the cluster: in `1794 17D2 1780` the suffix
`1780` is strong, and the regex says STRONG. With three or more coengs, the regex can
also miss a strong consonant that the prose counts. The oracle follows the regex.
**Resolution:** where the two disagree, leave the -u unchanged and flag it (O7). Q-008
asks which reading is right.

## Differences from the oracle

With default options and Khmer-only input, `normalize(x)` equals `khnormal(NFC(x))`
except in the cases below. The test suite checks each one.

| # | Case | Oracle | Pheasa | Reason |
|---|---|---|---|---|
| O1 | Sorted cluster ends in COENG or ZWJ before a base (rule 2.3) | sorts; its output is not a fixed point, e.g. `1780 17D2 17CC 1781 17CC` → `1780 17CC 17D2 1781 17CC` → `1780 17CC 17CC 17D2 1781` | leaves the cluster as typed | Idempotence (test requirement 2) and "a dangling COENG is flagged, not silently fixed" |
| O2 | Sorted cluster would end before a non-Khmer mark that NFC swaps with it (rule 2.3) | sorts; output is not NFC | leaves the cluster as typed | NFC invariance (test requirement 3). Needs non-Khmer input, so the Khmer-only differential test never sees it |
| O3 | Leading U+FEFF (rule 1.1) | keeps it | removes it | Pheasa policy (Stage 1) |
| O4 | A fold leaves the cluster unsorted or exposes another fold (rule 3.9), e.g. `179F 17C1 17BB 17B7` or three coengs with coeng ro first | one pass; its output is not a fixed point (`179F 17C1 17CA 17B7`) | repeats until stable (`179F 17CA 17C1 17B7`) | Idempotence |
| O5 | -u after a cluster whose consonants are NYO (1789) and other weak letters (rule 3.6) | leaves the -u: its S2 class has 1780 where UTN61 p. 23 has 1789 | 17C9 | UTN61 pp. 18, 23 list 1789 as weak. The oracle copies a typo from UTN61 p. 24 |
| O6 | -u before 17D0 after a STRONG cluster, or after a WEAK cluster with pre-base vowel 17C4 or 17C5 (rule 3.6) | 17CA, or 17C9 | leaves the -u | UTN61 p. 25 (samyok sannya does not push triisap down) and p. 16 (AboveVowelSamyok allows only 17C1–17C3). Converting would change the rendering |
| O7 | -u where UTN61's prose and regex disagree (BA followed by a strong consonant, or 3+ coengs), or where the consonant cluster is outside `Base Robat? Coengs` (e.g. two robats) (rule 3.6) | follows the regex, matched against any suffix of the cluster | leaves the -u and flags it | Conflict C4. Sources disagree, so the conservative choice applies |

The differential test (`tests/test_normalize.py`) accepts a difference only when one of
these rows can apply: O1 shows up as a new joiner + base pair in the oracle's output, O4
as oracle output that the oracle itself changes, and O5–O7 need a -u together with
17D0, NYO, BA, three coengs or two robats. O2 and O3 need input outside the Khmer-only
alphabet the test uses.

## Known defects in the reference material

- **The PDF listing of `khnormal` (UTN61 p. 38) differs from the GitHub version.** It
  passes `re.X` as the positional `count` argument of `re.sub`. As a result the STRONG
  and NSTRONG verbose patterns are never compiled as verbose, and rule 3.6 never fires.
  The GitHub version (`flags=re.X`) is correct, and it is the oracle.
- **Lunar-date conversion never runs** (see Stage 3).
- **UTN61 p. 24 lists `1780` in S2B.** The same class on p. 23, and WeakBase on p. 18,
  have `1789` (NYO) instead, and 1780 is already a strong consonant. The oracle copies
  the p. 24 version, so -u after NYO is never converted (O5).
- **UTN61 p. 16 NonBA lists only consonants.** p. 24 treats independent vowels as weak
  bases that are not BA, and SIL's NonBA includes them. Pheasa includes them in the C4
  regex check.

## Output stability

`NORMALIZATION_VERSION = "1"` fixes the behavior described here. Any change to the
output for any input needs a new version, a CHANGELOG entry, and a DECISIONS entry.

## Test requirements (Phase 1b)

1. **Differential:** for Khmer-only generated text, `normalize(x)` equals
   `khnormal(NFC(x))` with all options at their defaults. Any difference must be listed
   in this document (see Differences from the oracle).
2. **Idempotence:** `normalize(normalize(x)) == normalize(x)`.
3. **NFC invariance:** `NFC(normalize(x)) == normalize(x)`.
4. **No lost bases:** the multiset of base characters is unchanged, except for
   `fold_deprecated`.
5. **Permutation:** every reordering of a valid cluster that renders identically
   normalizes to the same output.
6. **Golden fixtures:** real text with provenance, with expected outputs verified by a
   native speaker.
7. **Rendering check (C1):** shape both shifter orders with HarfBuzz and compare the
   glyph output.
