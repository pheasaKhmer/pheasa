//! Khmer text normalization: the Rust port of the Python package `pheasa`.
//!
//! [`normalize`] makes Khmer text that looks identical also byte-identical. It puts every
//! syllable into the order defined by Unicode Technical Note #61, replaces "do not use"
//! sequences with their preferred equivalents and applies the options in [`Options`].
//! It does not correct spelling. The rules are specified in `spec/normalization.md` in
//! the pheasa repository; rule numbers in the source refer to that document.
//!
//! ```
//! use pheasa::{Options, Zwsp, normalize, normalize_with};
//!
//! // U+1781 U+17C2 U+17D2 U+1798 U+179A becomes U+1781 U+17D2 U+1798 U+17C2 U+179A.
//! assert_eq!(normalize("ខែ្មរ"), "ខ្មែរ");
//!
//! let options = Options { zwsp: Zwsp::Strip, ..Options::default() };
//! assert_eq!(normalize_with("ក\u{200B}ខ", options), "កខ");
//! ```
//!
//! # Same output as Python
//!
//! The Python implementation is the reference. For every input and every combination of
//! options, this crate returns the same text as Python's `pheasa.normalize`, and
//! [`NORMALIZATION_VERSION`] names the rule set of both. The tests hold the port to cases
//! generated from the Python implementation (`tests/fixtures/parity.tsv`, written by
//! `scripts/export_rust_fixtures.py`; decision D-015).
//!
//! Two limits follow from the platforms rather than the rules. A Rust string cannot hold
//! a lone surrogate, which a Python string can. And NFC (rule 1.3) of non-Khmer text uses
//! the Unicode data of the `unicode-normalization` crate, Unicode 17.0.0, while Python
//! uses its interpreter's `unicodedata`. NFC of a character never changes once it is
//! assigned, so the two agree on text whose characters are assigned in both Unicode
//! versions. The Khmer tables are written out in the source from Unicode 18.0.0, whose
//! Khmer entries are the same as in 15.1.0 and 17.0.0 (D-006).
//!
//! # Not ported
//!
//! This first port covers the normalized text only. Python's `normalize(text,
//! report=True)`, which also returns every change with input offsets and the issues left
//! in the text, and `pheasa.validate` have no Rust equivalent yet.

mod cluster;
mod fold;

use unicode_normalization::{IsNormalized, UnicodeNormalization, is_nfc_quick};

/// Names the rule set of `spec/normalization.md` that [`normalize`] implements.
///
/// Python's `pheasa.NORMALIZATION_VERSION` has the same value, and both implementations
/// give the same output for it. Any change to the output for any input needs a new
/// version (D-013). Store the version next to anything you hash.
pub const NORMALIZATION_VERSION: &str = "1";

const BOM: char = '\u{FEFF}';
const ZWSP: char = '\u{200B}';

/// What to do with U+200B ZERO WIDTH SPACE (Python's `zwsp` option).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum Zwsp {
    /// Keep it (`"keep"`). ZWSP is the recommended way to mark Khmer word boundaries.
    #[default]
    Keep,
    /// Remove it (`"strip"`).
    Strip,
    /// Replace it with U+0020 SPACE (`"space"`).
    Space,
}

/// Conversion between Khmer and ASCII digits (Python's `digits` option).
///
/// Only U+17E0–17E9 and U+0030–0039 are converted. The divination numerals U+17F0–17F9
/// never are.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum Digits {
    /// Leave digits as they are (`"keep"`).
    #[default]
    Keep,
    /// Convert 0–9 to U+17E0–17E9 (`"khmer"`).
    Khmer,
    /// Convert U+17E0–17E9 to 0–9 (`"ascii"`).
    Ascii,
}

/// Options of [`normalize_with`]. The default is [`normalize`]'s behavior.
///
/// Each field is the Python keyword argument of the same name. All are off by default,
/// because each one removes or rewrites information (spec Stage 4 and rule 3.8).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub struct Options {
    /// Keep coeng da (U+17D2 U+178A) instead of storing it as coeng ta (rule 3.8).
    pub preserve_coeng_da: bool,
    /// What to do with U+200B ZERO WIDTH SPACE.
    pub zwsp: Zwsp,
    /// Conversion between Khmer and ASCII digits.
    pub digits: Digits,
    /// Replace the deprecated characters U+17A3, U+17A4 and U+17D8, and remove U+17B4 and
    /// U+17B5.
    pub fold_deprecated: bool,
}

/// Returns the normalized form of `text` with default options.
///
/// The same as Python's `pheasa.normalize(text)`.
#[must_use]
pub fn normalize(text: &str) -> String {
    normalize_with(text, Options::default())
}

/// Returns the normalized form of `text` with the given options.
///
/// The same as Python's `pheasa.normalize(text, **options)`.
#[must_use]
pub fn normalize_with(text: &str, options: Options) -> String {
    let text = pre_clean(text, options);
    reorder(&text, options.preserve_coeng_da)
}

// --- Stage 1 and Stage 4 (applied during pre-clean, before NFC; see spec "Pipeline") ---

// Source: UCD 18.0.0 (17E0-17E9 are gc=Nd with decimal values 0-9). 17F0-17F9 are gc=No
// divination numerals and are never converted.
const KHMER_DIGITS: [char; 10] = [
    '\u{17E0}', '\u{17E1}', '\u{17E2}', '\u{17E3}', '\u{17E4}', '\u{17E5}', '\u{17E6}', '\u{17E7}',
    '\u{17E8}', '\u{17E9}',
];
const ASCII_DIGITS: [char; 10] = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

impl Options {
    /// Stage 4: appends what `ch` becomes to `out`.
    fn substitute(self, ch: char, out: &mut Vec<char>) {
        match ch {
            ZWSP => match self.zwsp {
                Zwsp::Keep => out.push(ch),
                Zwsp::Strip => {}
                Zwsp::Space => out.push(' '),
            },
            '0'..='9' if self.digits == Digits::Khmer => {
                out.push(convert(ch, ASCII_DIGITS, KHMER_DIGITS));
            }
            '\u{17E0}'..='\u{17E9}' if self.digits == Digits::Ascii => {
                out.push(convert(ch, KHMER_DIGITS, ASCII_DIGITS));
            }
            // Source: UTN #61 pp. 27, 30 (intentional confusables); TUS 18.0 §16.4
            // (deprecated and discouraged characters). 17B4 and 17B5 are
            // Default_Ignorable (UTN #61 p. 27).
            '\u{17A3}' if self.fold_deprecated => out.push('\u{17A2}'),
            '\u{17A4}' if self.fold_deprecated => out.extend(['\u{17A2}', '\u{17B6}']),
            '\u{17D8}' if self.fold_deprecated => out.extend(['\u{17D4}', '\u{179B}', '\u{17D4}']),
            '\u{17B4}' | '\u{17B5}' if self.fold_deprecated => {}
            _ => out.push(ch),
        }
    }
}

/// The digit in `to` at the position of `digit` in `from`.
fn convert(digit: char, from: [char; 10], to: [char; 10]) -> char {
    from.iter()
        .position(|&d| d == digit)
        .map_or(digit, |value| to[value])
}

/// Rule 1.1, the Stage 4 options, then rule 1.3 (the spec's execution order).
fn pre_clean(text: &str, options: Options) -> Vec<char> {
    // Rule 1.1: a leading byte order mark (or a run of them) is not text.
    // Source: TUS 18.0 §23.8
    let text = text.trim_start_matches(BOM);
    // Stage 4 runs here so that its output is normalized like any other text.
    let mut chars = Vec::with_capacity(text.len());
    for ch in text.chars() {
        options.substitute(ch, &mut chars);
    }
    // Rule 1.3. Source: UAX #15. The quick check answers "yes" only for text that is
    // already NFC, which is most text.
    if is_nfc_quick(chars.iter().copied()) == IsNormalized::Yes {
        chars
    } else {
        chars.into_iter().nfc().collect()
    }
}

// --- Stages 2 and 3 --------------------------------------------------------------------

/// Stages 2 and 3: normalizes each syllable cluster in turn.
fn reorder(text: &[char], preserve_coeng_da: bool) -> String {
    let mut out = String::with_capacity(text.iter().map(|ch| ch.len_utf8()).sum());
    let mut done = 0;
    for (i, j) in cluster::clusters(text) {
        if j - i <= 2 {
            continue; // a base plus one mark is always already in order and has no fold
        }
        let cluster = &text[i..j];
        let result = normalize_cluster(cluster, preserve_coeng_da);
        // Rule 2.3: keep the cluster as typed if the result would disturb its neighbour.
        if result != cluster
            && text
                .get(j)
                .is_none_or(|&next| cluster::is_stable(&result, next))
        {
            out.extend(&text[done..i]);
            out.extend(&result);
            done = j;
        }
    }
    out.extend(&text[done..]);
    out
}

/// Stages 2 and 3 on one cluster, repeated until the result no longer changes.
///
/// A fold can leave the cluster unsorted or expose another fold (rule 3.9). Each round
/// either shortens the cluster, removes a -u, 17BE or coeng da, or only permutes it, and
/// a round after a permutation-only round changes nothing, so the loop ends.
fn normalize_cluster(cluster: &[char], preserve_coeng_da: bool) -> Vec<char> {
    let mut cluster = cluster.to_vec();
    loop {
        let mut result = cluster::sort(&cluster);
        fold::fold(&mut result, preserve_coeng_da);
        if result == cluster {
            return cluster;
        }
        cluster = result;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn digits_convert_both_ways() {
        for (ascii, khmer) in ASCII_DIGITS.into_iter().zip(KHMER_DIGITS) {
            assert_eq!(convert(ascii, ASCII_DIGITS, KHMER_DIGITS), khmer);
            assert_eq!(convert(khmer, KHMER_DIGITS, ASCII_DIGITS), ascii);
        }
        assert_eq!(KHMER_DIGITS[9], '\u{17E9}');
    }

    #[test]
    fn cluster_loop_reaches_a_fixed_point() {
        // Rule 3.9: the -u left over after 3.6 is sorted and 3.5 applied again.
        let source: Vec<char> = "\u{1798}\u{17BB}\u{17BE}\u{17BB}".chars().collect();
        let expected: Vec<char> = "\u{1798}\u{17C9}\u{17BB}\u{17BE}".chars().collect();
        assert_eq!(normalize_cluster(&source, false), expected);
        assert_eq!(normalize_cluster(&expected, false), expected);
    }
}
