//! Stage 2: syllable clusters, their sort keys and the stability guard (rules 2.1–2.3).

use unicode_normalization::char::canonical_combining_class;

pub(crate) const COENG: char = '\u{17D2}';
pub(crate) const ZWNJ: char = '\u{200C}';
pub(crate) const ZWJ: char = '\u{200D}';
const ATTHACAN: char = '\u{17DD}';

/// Sort key of a character inside a syllable cluster (spec Stage 2 table).
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Key {
    /// Ends a cluster, never moved.
    Other,
    Base,
    Robat,
    /// COENG and the base it subjoins.
    Coeng,
    Shifter,
    Zwnj,
    VowelPre,
    VowelBelow,
    VowelAbove,
    VowelPost,
    Modifier,
    Final,
    /// ZWJ, and every COENG or base chained after it.
    FinalCoeng,
}

/// The sort key of `ch` on its own, before joiners are taken into account.
#[expect(
    clippy::match_same_arms,
    reason = "one arm per row of the spec's table, each with its source"
)]
pub(crate) fn key(ch: char) -> Key {
    match ch {
        // Source: UTN #61 p. 16 (consonants are bases)
        '\u{1780}'..='\u{17A2}' => Key::Base,
        // Source: UTN #61 p. 13; TUS 18.0 §16.4 (deprecated independent vowels are Other)
        '\u{17A3}'..='\u{17A4}' => Key::Other,
        // Source: UTN #61 p. 16 (independent vowels are bases)
        '\u{17A5}'..='\u{17B3}' => Key::Base,
        // Source: UTN #61 p. 13 (inherent vowels 17B4, 17B5 are Other)
        '\u{17B4}'..='\u{17B5}' => Key::Other,
        // Source: UTN #61 p. 16 (vowel slot); SIL khnormal categories (vowel sub-order)
        '\u{17B6}' => Key::VowelPost,
        '\u{17B7}'..='\u{17BA}' => Key::VowelAbove,
        '\u{17BB}'..='\u{17BD}' => Key::VowelBelow,
        '\u{17BE}'..='\u{17C5}' => Key::VowelPre,
        // Source: UTN #61 p. 16 (modifier and final slots)
        '\u{17C6}' => Key::Modifier,
        '\u{17C7}'..='\u{17C8}' => Key::Final,
        // Source: UTN #61 pp. 16, 25 (shifters follow the coengs; spec conflict C1)
        '\u{17C9}'..='\u{17CA}' => Key::Shifter,
        '\u{17CB}' => Key::Modifier,
        // Source: UTN #61 p. 16 (robat directly follows the base)
        '\u{17CC}' => Key::Robat,
        '\u{17CD}'..='\u{17D1}' => Key::Modifier,
        // Source: UTN #61 p. 16
        COENG => Key::Coeng,
        // Source: SIL khnormal categories; UTN #61 pp. 13, 16 say Other (spec conflict C3)
        '\u{17D3}' => Key::Modifier,
        // Source: UTN #61 p. 13 (punctuation and currency signs are Other)
        '\u{17D4}'..='\u{17DC}' => Key::Other,
        // Source: UTN #61 p. 16
        ATTHACAN => Key::Modifier,
        // Source: UTN #61 p. 16 (ZWNJ after a shifter)
        ZWNJ => Key::Zwnj,
        // Source: UTN #61 pp. 14-15 (ZWJ marks a final coeng)
        ZWJ => Key::FinalCoeng,
        _ => Key::Other,
    }
}

/// Is `ch` a base: a consonant (U+1780–17A2) or an independent vowel (U+17A5–17B3)?
pub(crate) fn is_base(ch: char) -> bool {
    key(ch) == Key::Base
}

/// A base or COENG right after one of these belongs to the unit the joiner opened (a
/// subscript, or a Middle Khmer final coeng) and takes the joiner's sort key.
/// Source: UTN #61 p. 16 (coeng + base is one unit); pp. 14-15 (ZWJ + coeng)
fn is_joiner(ch: char) -> bool {
    ch == COENG || ch == ZWJ
}

/// Sort key of `text[j]` inside a cluster, given the key of `text[j - 1]`.
fn key_at(text: &[char], j: usize, previous: Key) -> Key {
    let key = key(text[j]);
    if matches!(key, Key::Base | Key::Coeng) && is_joiner(text[j - 1]) {
        previous
    } else {
        key
    }
}

/// Canonical combining class. Only U+17D2 (9) and U+17DD (230) have one among the Khmer
/// characters. Source: UCD 18.0.0 `UnicodeData.txt`; the rest comes from the
/// `unicode-normalization` crate, as it does for NFC.
fn ccc(ch: char) -> u8 {
    match ch {
        COENG => 9,
        ATTHACAN => 230,
        _ => canonical_combining_class(ch),
    }
}

/// The `(start, end)` span of every syllable cluster in `text` (rule 2.1).
pub(crate) fn clusters(text: &[char]) -> impl Iterator<Item = (usize, usize)> {
    let mut i = 0;
    std::iter::from_fn(move || {
        while i < text.len() {
            // A cluster starts at a base that is not part of a joiner unit.
            if !is_base(text[i]) || (i > 0 && is_joiner(text[i - 1])) {
                i += 1;
                continue;
            }
            let start = i;
            let mut key = Key::Base;
            i += 1;
            while i < text.len() {
                key = key_at(text, i, key);
                if key <= Key::Base {
                    break;
                }
                i += 1;
            }
            return Some((start, i));
        }
        None
    })
}

/// Rule 2.2: sorts a cluster by key. The sort is stable, so typed order is kept within a
/// key.
pub(crate) fn sort(cluster: &[char]) -> Vec<char> {
    let mut keyed = Vec::with_capacity(cluster.len());
    let mut previous = Key::Base;
    for (j, &ch) in cluster.iter().enumerate() {
        // The first character is the cluster's base.
        let key = if j == 0 {
            Key::Base
        } else {
            key_at(cluster, j, previous)
        };
        keyed.push((key, ch));
        previous = key;
    }
    keyed.sort_by_key(|&(key, _)| key);
    keyed.into_iter().map(|(_, ch)| ch).collect()
}

/// Rule 2.3: can the sorted cluster be emitted without changing the character after it?
pub(crate) fn is_stable(ordered: &[char], following: char) -> bool {
    let Some(&last) = ordered.last() else {
        return true;
    };
    // A trailing COENG or ZWJ would pull the next syllable's base into this cluster, so
    // normalizing the output again would give a different result.
    if is_joiner(last) && is_base(following) {
        return false;
    }
    // NFC would reorder the cluster's last mark with the next character.
    let ccc_next = ccc(following);
    !(0 < ccc_next && ccc_next < ccc(last))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chars(text: &str) -> Vec<char> {
        text.chars().collect()
    }

    #[test]
    fn keys_follow_the_spec_table() {
        assert_eq!(key('\u{1780}'), Key::Base);
        assert_eq!(key('\u{17B3}'), Key::Base);
        assert_eq!(key('\u{17B4}'), Key::Other);
        assert_eq!(key('\u{17D3}'), Key::Modifier);
        assert_eq!(key('\u{17DE}'), Key::Other);
        assert_eq!(key('\u{25CC}'), Key::Other);
        assert_eq!(key(ZWNJ), Key::Zwnj);
        assert_eq!(key(ZWJ), Key::FinalCoeng);
    }

    #[test]
    fn khmer_combining_classes_match_the_crate() {
        let khmer = ('\u{1780}'..='\u{17FF}').chain('\u{19E0}'..='\u{19FF}');
        for ch in khmer {
            assert_eq!(
                ccc(ch),
                canonical_combining_class(ch),
                "U+{:04X}",
                u32::from(ch)
            );
        }
    }

    #[test]
    fn clusters_skip_joined_bases_and_marks_without_base() {
        // U+17B6 alone, then KA + coeng KHA + AA, then a space, then KA.
        let text = chars("\u{17B6}\u{1780}\u{17D2}\u{1781}\u{17B6} \u{1780}");
        assert_eq!(clusters(&text).collect::<Vec<_>>(), [(1, 5), (6, 7)]);
    }

    #[test]
    fn sort_keeps_subscripts_together() {
        let typed = chars("\u{1781}\u{17C2}\u{17D2}\u{1798}");
        assert_eq!(sort(&typed), chars("\u{1781}\u{17D2}\u{1798}\u{17C2}"));
    }

    #[test]
    fn trailing_joiner_before_a_base_is_unstable() {
        assert!(!is_stable(&chars("\u{1780}\u{17CC}\u{17D2}"), '\u{1781}'));
        assert!(is_stable(&chars("\u{1780}\u{17CC}\u{17D2}"), ' '));
        // ATTHACAN (230) before U+0316 (220) would be swapped by NFC.
        assert!(!is_stable(&chars("\u{1780}\u{17B6}\u{17DD}"), '\u{0316}'));
        assert!(is_stable(&chars("\u{1780}\u{17B6}\u{17DD}"), '\u{0300}'));
    }
}
