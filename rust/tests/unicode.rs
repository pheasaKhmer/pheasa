//! The Unicode data behind NFC (rule 1.3). See the crate documentation and D-015.

use unicode_normalization::char::canonical_combining_class;
use unicode_normalization::{UNICODE_VERSION, UnicodeNormalization};

#[test]
fn nfc_data_is_unicode_17() {
    // A new version of `unicode-normalization` can change NFC of non-Khmer text, and so
    // the output. Updating it means checking parity with Python again (D-015).
    assert_eq!(UNICODE_VERSION, (17, 0, 0));
}

#[test]
fn no_khmer_character_decomposes() {
    // UCD 18.0.0: no character in U+1780-17FF or U+19E0-19FF has a decomposition, and
    // only U+17D2 (9) and U+17DD (230) have a combining class (spec rule 1.3).
    for ch in ('\u{1780}'..='\u{17FF}').chain('\u{19E0}'..='\u{19FF}') {
        let alone = ch.to_string();
        assert_eq!(alone.nfd().collect::<String>(), alone);
        assert_eq!(alone.nfc().collect::<String>(), alone);
        let expected = match ch {
            '\u{17D2}' => 9,
            '\u{17DD}' => 230,
            _ => 0,
        };
        assert_eq!(
            canonical_combining_class(ch),
            expected,
            "U+{:04X}",
            u32::from(ch)
        );
    }
}

#[test]
fn nfc_moves_coeng_before_atthacan() {
    // Spec rule 1.3 and UTN #61 pp. 27-28.
    let typed = "\u{1780}\u{17DD}\u{17D2}\u{179A}";
    assert_eq!(
        typed.nfc().collect::<String>(),
        "\u{1780}\u{17D2}\u{17DD}\u{179A}"
    );
}
