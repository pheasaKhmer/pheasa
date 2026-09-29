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

`normalize(text, **options)` runs these stages in order. Stages 2 and 3 are the UTN61
core and must match the SIL oracle. Stages 1 and 4 are Pheasa's own policy.

```
1. pre-clean   BOM, NFC                            (Pheasa policy)
2. reorder     sort each syllable cluster          (UTN61)
3. fold        do-not-use sequences -> preferred   (UTN61)
4. options     ZWSP, digits, deprecated chars      (Pheasa policy, opt-in)
   validate    flag non-conformant syllables       (UTN61 khtest; never modifies text)
```

---

## Stage 1: pre-clean

| # | Rule | Default | Source |
|---|---|---|---|
| 1.1 | Remove a single U+FEFF at the start of the text. | on | TUS §23.8. Since Unicode 3.2, U+FEFF is used only as a byte order mark and not as a zero-width no-break space. |
| 1.2 | U+FEFF elsewhere is preserved and flagged. | on | Same as 1.1. Mid-text use is ambiguous, so it is not silently removed. |
| 1.3 | Apply NFC. | on | UAX15. For Khmer text NFC is nearly a no-op: no Khmer character decomposes, and only U+17D2 (ccc=9) and U+17DD (ccc=230) have a non-zero combining class (UCD; UTN61 p. 27). NFC runs for the benefit of non-Khmer text in mixed strings. |

**Invariant:** `NFC(normalize(x)) == normalize(x)`. Pheasa output must survive a
downstream NFC unchanged. UTN61 pp. 27–28 notes that NFC reorders `<17DD 17D2>` to
`<17D2 17DD>`. Under UTN61's structure, a coeng after ATTHACAN is a final coeng, which
is Middle Khmer only and always marked with ZWJ. ZWJ has ccc=0, so it blocks the
reorder. Property tests must confirm this.

## Stage 2: reorder syllable clusters

A cluster starts at a base character: a consonant U+1780–17A2 or an independent vowel
U+17A5–17B3 (UTN61 p. 16), plus U+25CC DOTTED CIRCLE as a placeholder (SIL `B` only). The cluster continues
through every following character in the categories below. Characters within a cluster
are stably sorted by category, so typed order is kept inside each category.

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
| 3.6 | -u (17BB) before an above vowel or 17D0, where a shifter was meant | 17CA after a STRONG cluster, 17C9 after a WEAK one | UTN61 pp. 24–25, 28–29 |
| 3.7 | `17D2 179A 17D2 X` (coeng ro first) | `17D2 X 17D2 179A` | UTN61 pp. 16, 29, 35 |
| 3.8 | `17D2 178A` (coeng da) | `17D2 178F` (coeng ta) | UTN61 pp. 31–32; default confirmed by native-speaker review (D-008). Option `preserve_coeng_da=True` disables it. |

STRONG and WEAK are the cluster classes defined in UTN61 pp. 16 and 24. Implement them
from the UTN61 grammar and check them against the SIL oracle.

**Not done in version 1:** UTN61 p. 35 says legacy "digit + coeng + khan" lunar-date
sequences should become U+19E0–19FF symbols. SIL's `khnormal` contains that
substitution, but it never runs: digits are Other, so they are never inside a cluster.
Pheasa version 1 matches the oracle's actual behavior (no conversion) and flags these
sequences. See D-009.

## Stage 4: options (Pheasa policy)

Everything here is outside UTN61's scope. Anything that removes or rewrites visible
information is off by default.

| Option | Default | Behavior | Source |
|---|---|---|---|
| `zwsp` | `"keep"` | `"keep"`, `"strip"`, or `"space"` for U+200B | TUS §16.4: ZWSP is the recommended way to mark Khmer word boundaries, so keeping it is the default. |
| `digits` | `"keep"` | `"keep"`, `"khmer"`, or `"ascii"`. Maps only U+17E0–17E9 ↔ U+0030–0039. | UCD: 17E0–17E9 are gc=Nd with decimal values 0–9. U+17F0–17F9 (LEK ATTAK) are gc=No divination numerals and are **never** converted. |
| `fold_deprecated` | `False` | 17A3→17A2; 17A4→17A2 17B6; 17D8→17D4 179B 17D4; remove 17B4 and 17B5 | UTN61 pp. 27, 30 (intentional confusables); TUS §16.4 (17A3 and 17A4 deprecated; 17B4 and 17B5 "should be considered errors"; 17D8 discouraged) |

ZWNJ and ZWJ are never removed, except as part of rule 3.1. UTN61 gives them roles:
ZWNJ after a shifter keeps it from downshifting (p. 16), and ZWJ marks a final coeng in
Middle Khmer (pp. 14–15). Occurrences anywhere else are flagged, not removed.

## Validation (report only)

`normalize(text, report=True)` also returns a list of changes and issues, each with a
character offset, a rule ID from this document, and the before and after code points.
Issues come from a port of SIL's `khtest` (the UTN61 syllable grammar, p. 16) and cover:

- a dangling coeng (17D2 not followed by a base);
- ZWNJ or ZWJ outside a permitted position;
- repeated vowels or modifiers, such as `1780 17B6 17B6`;
- a mid-text U+FEFF;
- legacy lunar-date sequences (see D-009);
- `17C4 17B8` produced by rule 3.2. This is valid under UTN61's Middle Khmer grammar but
  not its Modern Khmer grammar, so it is flagged for review.

Validation never modifies text.

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

**Phase 1b task:** confirm with HarfBuzz and a common Khmer font that both orders render
identically.

**C2. ZWNJ position.** The TUS §16.4 grammar allows ZWNJ or ZWJ before a dependent vowel
(`{Z} V`). UTN61 allows ZWNJ only after a shifter. **Resolution:** preserve and flag,
never remove.

**C3. U+17D3.** UTN61 treats it as Other; SIL's code treats it as a modifier. **Resolution:** follow the oracle and flag it (see Stage 2).

## Known defects in the reference material

- **The PDF listing of `khnormal` (UTN61 p. 38) differs from the GitHub version.** It
  passes `re.X` as the positional `count` argument of `re.sub`. As a result the STRONG
  and NSTRONG verbose patterns are never compiled as verbose, and rule 3.6 never fires.
  The GitHub version (`flags=re.X`) is correct, and it is the oracle.
- **Lunar-date conversion never runs** (see Stage 3).

## Output stability

`NORMALIZATION_VERSION = "1"` fixes the behavior described here. Any change to the
output for any input needs a new version, a CHANGELOG entry, and a DECISIONS entry.

## Test requirements (Phase 1b)

1. **Differential:** for Khmer-only generated text, `normalize(x)` equals
   `khnormal(NFC(x))` with all options at their defaults. Any difference must be listed
   in this document.
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
