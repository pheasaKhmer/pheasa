//! Stage 3: folds of "do not use" sequences in a sorted cluster (rules 3.1–3.8).
//!
//! The Python implementation uses regular expressions and `str.replace`. Each function
//! here performs the same substitution: matches are found left to right in the original
//! text, do not overlap, and are all replaced in one pass.

use crate::cluster::{COENG, ZWJ, ZWNJ, is_base};

const ROBAT: char = '\u{17CC}';
const U: char = '\u{17BB}';
const E: char = '\u{17C1}';
const BA: char = '\u{1794}';
const RO: char = '\u{179A}';
const MUUSIKATOAN: char = '\u{17C9}';
const TRIISAP: char = '\u{17CA}';
const SAMYOK_SANNYA: char = '\u{17D0}';

/// Stage 3: replaces "do not use" sequences in a sorted cluster, in spec order.
pub(crate) fn fold(text: &mut Vec<char>, preserve_coeng_da: bool) {
    // Rule 3.1. Source: SIL khnormal (repeated invisible characters after a coeng)
    drop_repeats_after_coeng(text);
    // Rule 3.2. Source: UTN #61 p. 29 (visually indistinct)
    replace_pair(text, ['\u{17BE}', '\u{17B6}'], ['\u{17C4}', '\u{17B8}']);
    // Rules 3.3 and 3.4. Source: UTN #61 p. 28 ("Do not use" table, split vowels)
    merge_split_vowel(text, '\u{17B8}', '\u{17BE}');
    merge_split_vowel(text, '\u{17B6}', '\u{17C4}');
    // Rule 3.5. Source: SIL khnormal; UTN #61 pp. 28, 30 (<17BE 17BB> stands for
    // shifter + 17BE)
    replace_pair(text, ['\u{17BE}', U], [U, '\u{17BE}']);
    // Rule 3.6
    u_to_shifter(text);
    // Rule 3.7, repeated so that a third coeng cannot leave coeng ro in front (spec O4).
    while move_coeng_ro_second(text) {}
    if !preserve_coeng_da {
        // Rule 3.8. Source: UTN #61 pp. 31-32; D-008
        replace_pair(text, [COENG, '\u{178A}'], [COENG, '\u{178F}']);
    }
}

/// Replaces every non-overlapping `from` pair with `to`, left to right.
fn replace_pair(text: &mut [char], from: [char; 2], to: [char; 2]) {
    let mut p = 0;
    while p + 1 < text.len() {
        if text[p..p + 2] == from {
            text[p..p + 2].copy_from_slice(&to);
            p += 2;
        } else {
            p += 1;
        }
    }
}

/// Rule 3.1: `(ZWJ? COENG)` followed by one or more of COENG, ZWNJ and ZWJ becomes the
/// first `(ZWJ? COENG)` alone. Python: `_REPEATED_AFTER_COENG.sub(r"\1", text)`.
fn drop_repeats_after_coeng(text: &mut Vec<char>) {
    let repeat = |ch: Option<&char>| matches!(ch, Some(&(COENG | ZWNJ | ZWJ)));
    let mut kept = Vec::with_capacity(text.len());
    let mut p = 0;
    while p < text.len() {
        // The length of the `(ZWJ? COENG)` group, if a repeated character follows it.
        let head = match text[p] {
            ZWJ if text.get(p + 1) == Some(&COENG) && repeat(text.get(p + 2)) => 2,
            COENG if repeat(text.get(p + 1)) => 1,
            _ => {
                kept.push(text[p]);
                p += 1;
                continue;
            }
        };
        kept.extend_from_slice(&text[p..p + head]);
        p += head;
        while repeat(text.get(p)) {
            p += 1;
        }
    }
    *text = kept;
}

/// Rules 3.3 and 3.4: `17C1 (17BB–17BD)? second` becomes `merged (17BB–17BD)?`. Python:
/// `_E_THEN_II` and `_E_THEN_AA`.
fn merge_split_vowel(text: &mut Vec<char>, second: char, merged: char) {
    let mut out = Vec::with_capacity(text.len());
    let mut p = 0;
    while p < text.len() {
        if text[p] == E {
            let below = text
                .get(p + 1)
                .copied()
                .filter(|ch| matches!(ch, '\u{17BB}'..='\u{17BD}'));
            if let Some(below) = below.filter(|_| text.get(p + 2) == Some(&second)) {
                out.extend([merged, below]);
                p += 3;
                continue;
            }
            if text.get(p + 1) == Some(&second) {
                out.push(merged);
                p += 2;
                continue;
            }
        }
        out.push(text[p]);
        p += 1;
    }
    *text = out;
}

/// Rule 3.6: a -u typed in place of a consonant shifter becomes the shifter.
///
/// The -u must follow the consonant cluster (UTN #61 p. 16: `Base Robat? Coengs`) at the
/// start of the text, directly or after one pre-base vowel. UTN #61 p. 18 (Middle Khmer
/// `AboveVowel`) allows 17C1–17C5 before the above vowel; the Stage 2 sort puts that
/// vowel before the -u.
fn u_to_shifter(text: &mut [char]) {
    if !text.first().is_some_and(|&ch| is_base(ch)) {
        return;
    }
    let mut end = 1;
    if text.get(end) == Some(&ROBAT) {
        end += 1;
    }
    while text.get(end) == Some(&COENG) && text.get(end + 1).is_some_and(|&ch| is_base(ch)) {
        end += 2;
    }
    let pre = text
        .get(end)
        .copied()
        .filter(|ch| matches!(ch, '\u{17C1}'..='\u{17C5}'));
    let u = end + usize::from(pre.is_some());
    if text.get(u) != Some(&U) {
        return;
    }
    let Some(shifter) = shifter_for_u(&text[..end], pre, &text[u + 1..]) else {
        return;
    };
    // The shifter goes in its Stage 2 position, before any pre-base vowel.
    text[end] = shifter;
    if let Some(pre) = pre {
        text[end + 1] = pre;
    }
}

/// Rule 3.6: the shifter a -u stands for, or `None` to leave the -u alone.
fn shifter_for_u(cluster: &[char], pre: Option<char>, after: &[char]) -> Option<char> {
    // Source: UTN #61 p. 16 (AboveVowel); 17B6 counts only with a following 17C6
    let above = matches!(
        after.first(),
        Some('\u{17B7}' | '\u{17B8}' | '\u{17B9}' | '\u{17BA}' | '\u{17BE}' | '\u{17DD}')
    ) || after.starts_with(&['\u{17B6}', '\u{17C6}']);
    if is_strong(cluster) {
        // UTN #61 p. 25: samyok sannya does not push triisap down (spec O6).
        return above.then_some(TRIISAP);
    }
    // UTN #61 p. 16: AboveVowelSamyok = AboveVowel | [17C1-17C3]? 17D0
    let samyok = after.first() == Some(&SAMYOK_SANNYA)
        && matches!(pre, None | Some('\u{17C1}'..='\u{17C3}'));
    (above || samyok).then_some(MUUSIKATOAN)
}

/// Is a consonant cluster (base, robat, coengs) STRONG?
///
/// UTN #61 p. 17 and p. 22 (rules 1-3): strong means it contains a series 1 consonant and
/// no BA. The p. 16 regex, used as a lookbehind, can disagree after a BA or with 3+
/// coengs; the prose wins (spec C4, Q-008, D-012). Independent vowels are weak (p. 24).
fn is_strong(cluster: &[char]) -> bool {
    let consonants = || cluster.iter().filter(|&&ch| ch != ROBAT && ch != COENG);
    !consonants().any(|&ch| ch == BA) && consonants().any(|&ch| is_strong_base(ch))
}

/// Source: UTN #61 p. 16 (`StrongBase`), p. 23 (S1 = `StrongBase`)
fn is_strong_base(ch: char) -> bool {
    matches!(
        ch,
        '\u{1780}'..='\u{1783}'
            | '\u{1785}'..='\u{1788}'
            | '\u{178A}'..='\u{178D}'
            | '\u{178F}'..='\u{1792}'
            | '\u{1795}'..='\u{1797}'
            | '\u{179E}'..='\u{17A0}'
            | '\u{17A2}'
    )
}

/// One pass of rule 3.7: `17D2 179A 17D2 X` becomes `17D2 X 17D2 179A` (coeng ro is the
/// second of two coengs; UTN #61 pp. 16, 29). Returns whether the text changed. Python:
/// `_COENG_RO_FIRST.sub(r"\2\1", text)`.
fn move_coeng_ro_second(text: &mut [char]) -> bool {
    let mut changed = false;
    let mut p = 0;
    while p + 3 < text.len() {
        if text[p] == COENG && text[p + 1] == RO && text[p + 2] == COENG && is_base(text[p + 3]) {
            let other = text[p + 3];
            text[p + 1..p + 4].copy_from_slice(&[other, COENG, RO]);
            changed |= other != RO;
            p += 4;
        } else {
            p += 1;
        }
    }
    changed
}

#[cfg(test)]
mod tests {
    use super::*;

    fn folded(text: &str) -> String {
        let mut chars: Vec<char> = text.chars().collect();
        fold(&mut chars, false);
        chars.into_iter().collect()
    }

    #[test]
    fn repeats_after_coeng_keep_the_first_joiner() {
        assert_eq!(
            folded("\u{1780}\u{17D2}\u{17D2}\u{1798}"),
            "\u{1780}\u{17D2}\u{1798}"
        );
        assert_eq!(
            folded("\u{1780}\u{200D}\u{17D2}\u{200C}\u{17D2}\u{1798}"),
            "\u{1780}\u{200D}\u{17D2}\u{1798}"
        );
        // ZWJ + COENG with nothing repeated after it is left alone.
        assert_eq!(
            folded("\u{1780}\u{200D}\u{17D2}"),
            "\u{1780}\u{200D}\u{17D2}"
        );
        // ZWNJ is not a head: the match starts at the COENG after it.
        assert_eq!(
            folded("\u{1780}\u{200C}\u{200D}\u{17D2}\u{200C}"),
            "\u{1780}\u{200C}\u{200D}\u{17D2}"
        );
    }

    #[test]
    fn split_vowels_merge() {
        assert_eq!(
            folded("\u{1780}\u{17C1}\u{17BC}\u{17B8}"),
            "\u{1780}\u{17BE}\u{17BC}"
        );
        assert_eq!(folded("\u{1780}\u{17C1}\u{17B6}"), "\u{1780}\u{17C4}");
        // A below vowel without the second half is left alone.
        assert_eq!(
            folded("\u{1780}\u{17C1}\u{17BC}"),
            "\u{1780}\u{17C1}\u{17BC}"
        );
    }

    #[test]
    fn u_becomes_a_shifter_before_the_pre_base_vowel() {
        // Strong cluster with pre-base vowel: triisap goes before 17C1 (spec O4).
        assert_eq!(
            folded("\u{179F}\u{17C1}\u{17BB}\u{17B7}"),
            "\u{179F}\u{17CA}\u{17C1}\u{17B7}"
        );
        // Weak cluster before samyok sannya.
        assert_eq!(
            folded("\u{1798}\u{17BB}\u{17D0}"),
            "\u{1798}\u{17C9}\u{17D0}"
        );
        // Strong cluster before samyok sannya: left alone (spec O6).
        assert_eq!(
            folded("\u{179F}\u{17BB}\u{17D0}"),
            "\u{179F}\u{17BB}\u{17D0}"
        );
        // Two robats are outside the cluster grammar (spec O8).
        let two_robats = "\u{179F}\u{17CC}\u{17CC}\u{17D2}\u{179A}\u{17BB}\u{17B9}";
        assert_eq!(folded(two_robats), two_robats);
    }

    #[test]
    fn strong_follows_the_prose() {
        // BA makes the cluster weak whatever else it contains (spec C4).
        assert!(!is_strong(&['\u{1794}', COENG, '\u{1780}']));
        assert!(is_strong(&[
            '\u{1798}', COENG, '\u{1798}', COENG, '\u{1780}'
        ]));
        // NYO is weak (spec O5); independent vowels are neither strong nor BA.
        assert!(!is_strong(&['\u{1789}']));
        assert!(!is_strong(&['\u{17A5}']));
    }

    #[test]
    fn coeng_ro_moves_behind_every_other_coeng() {
        let typed = "\u{1780}\u{17D2}\u{179A}\u{17D2}\u{1781}\u{17D2}\u{1782}";
        assert_eq!(
            folded(typed),
            "\u{1780}\u{17D2}\u{1781}\u{17D2}\u{1782}\u{17D2}\u{179A}"
        );
        // Two coeng ro: swapping them changes nothing, so the loop stops.
        let two_ro = "\u{1780}\u{17D2}\u{179A}\u{17D2}\u{179A}";
        assert_eq!(folded(two_ro), two_ro);
    }

    #[test]
    fn coeng_da_folds_unless_preserved() {
        assert_eq!(
            folded("\u{1780}\u{17D2}\u{178A}"),
            "\u{1780}\u{17D2}\u{178F}"
        );
        let mut kept: Vec<char> = "\u{1780}\u{17D2}\u{178A}".chars().collect();
        fold(&mut kept, true);
        assert_eq!(kept, ['\u{1780}', COENG, '\u{178A}']);
    }
}
