//! Examples of each rule, ported from the Python tests (`tests/test_normalize.py` and
//! `tests/test_options.py`). Rule numbers refer to `spec/normalization.md`.

use pheasa::{Digits, NORMALIZATION_VERSION, Options, Zwsp, normalize, normalize_with};

fn cps(code_points: &[u32]) -> String {
    code_points
        .iter()
        .map(|&cp| char::from_u32(cp).unwrap())
        .collect()
}

#[test]
fn public_api() {
    assert_eq!(NORMALIZATION_VERSION, "1");
    assert_eq!(normalize("abc"), normalize_with("abc", Options::default()));
}

#[test]
fn rule_examples() {
    let examples: &[(&str, &[u32], &[u32])] = &[
        // Stage 2 example (README): vowel typed before the subscript
        (
            "2.2",
            &[0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A],
            &[0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A],
        ),
        // Conflict C1: shifter moves after the coeng
        (
            "C1",
            &[0x1798, 0x17C9, 0x17D2, 0x1784, 0x17C3],
            &[0x1798, 0x17D2, 0x1784, 0x17C9, 0x17C3],
        ),
        // Robat before coeng, ZWNJ after shifter, modifier before final
        (
            "2.2",
            &[
                0x1780, 0x17C7, 0x17B6, 0x200C, 0x17CA, 0x17D2, 0x1781, 0x17CC,
            ],
            &[
                0x1780, 0x17CC, 0x17D2, 0x1781, 0x17CA, 0x200C, 0x17B6, 0x17C7,
            ],
        ),
        // Same key keeps typed order: two above vowels are not swapped
        ("2.2", &[0x1780, 0x17B8, 0x17B7], &[0x1780, 0x17B8, 0x17B7]),
        // A final coeng (ZWJ unit) sorts last
        (
            "2.2",
            &[0x1780, 0x200D, 0x17D2, 0x1781, 0x17B6],
            &[0x1780, 0x17B6, 0x200D, 0x17D2, 0x1781],
        ),
        ("1.1", &[0xFEFF, 0x1780], &[0x1780]),
        ("1.1", &[0xFEFF, 0xFEFF, 0x1780], &[0x1780]),
        ("1.2", &[0x1780, 0xFEFF, 0x1781], &[0x1780, 0xFEFF, 0x1781]),
        ("1.3", &[0x65, 0x301], &[0xE9]),
        // NFC puts COENG (ccc 9) before ATTHACAN (ccc 230), which detaches the subscript.
        (
            "1.3",
            &[0x1780, 0x17DD, 0x17D2, 0x179A],
            &[0x1780, 0x17D2, 0x17DD, 0x179A],
        ),
        // ZWSP ends a cluster and is kept
        ("2.1", &[0x1780, 0x200B, 0x17B6], &[0x1780, 0x200B, 0x17B6]),
        // A dotted circle is not a cluster start
        (
            "2.1",
            &[0x25CC, 0x17B6, 0x17D2, 0x1781],
            &[0x25CC, 0x17B6, 0x17D2, 0x1781],
        ),
        // Marks with no base before them are left alone
        (
            "2.1",
            &[0x0041, 0x17B6, 0x17D2, 0x1780],
            &[0x0041, 0x17B6, 0x17D2, 0x1780],
        ),
        // Deprecated characters are Other: untouched
        ("2.1", &[0x17A3, 0x17B6], &[0x17A3, 0x17B6]),
        (
            "3.1",
            &[0x1780, 0x17D2, 0x17D2, 0x1798],
            &[0x1780, 0x17D2, 0x1798],
        ),
        (
            "3.1",
            &[0x1780, 0x17D2, 0x200C, 0x200D, 0x1798],
            &[0x1780, 0x17D2, 0x1798],
        ),
        ("3.2", &[0x1780, 0x17BE, 0x17B6], &[0x1780, 0x17C4, 0x17B8]),
        ("3.3", &[0x1780, 0x17C1, 0x17B8], &[0x1780, 0x17BE]),
        (
            "3.3",
            &[0x1780, 0x17C1, 0x17BC, 0x17B8],
            &[0x1780, 0x17BE, 0x17BC],
        ),
        ("3.4", &[0x1780, 0x17C1, 0x17B6], &[0x1780, 0x17C4]),
        // 3.5 then 3.6: <17BE 17BB> after a strong cluster is triisap + 17BE
        ("3.5", &[0x179F, 0x17BE, 0x17BB], &[0x179F, 0x17CA, 0x17BE]),
        ("3.6", &[0x179F, 0x17BB, 0x17B8], &[0x179F, 0x17CA, 0x17B8]),
        ("3.6", &[0x1798, 0x17BB, 0x17B8], &[0x1798, 0x17C9, 0x17B8]),
        ("3.6", &[0x1798, 0x17BB, 0x17D0], &[0x1798, 0x17C9, 0x17D0]),
        (
            "3.6",
            &[0x1798, 0x17BB, 0x17B6, 0x17C6],
            &[0x1798, 0x17C9, 0x17B6, 0x17C6],
        ),
        // BA makes a cluster weak even with a strong consonant before it (UTN #61 p. 22)
        (
            "3.6",
            &[0x179F, 0x17D2, 0x1794, 0x17BB, 0x17B7],
            &[0x179F, 0x17D2, 0x1794, 0x17C9, 0x17B7],
        ),
        // -u before a vowel that is not above-base stays -u
        ("3.6", &[0x179F, 0x17BB, 0x17B6], &[0x179F, 0x17BB, 0x17B6]),
        (
            "3.7",
            &[0x179F, 0x17D2, 0x179A, 0x17D2, 0x1780],
            &[0x179F, 0x17D2, 0x1780, 0x17D2, 0x179A],
        ),
        ("3.8", &[0x1780, 0x17D2, 0x178A], &[0x1780, 0x17D2, 0x178F]),
        // A base DA is not a coeng: only coeng da folds
        ("3.8", &[0x178A, 0x17B6], &[0x178A, 0x17B6]),
        // Rule 3.9: the -u left over after 3.6 is sorted and 3.5 applied again
        (
            "3.9",
            &[0x1798, 0x17BB, 0x17BE, 0x17BB],
            &[0x1798, 0x17C9, 0x17BB, 0x17BE],
        ),
    ];
    for &(rule, source, expected) in examples {
        assert_eq!(
            normalize(&cps(source)),
            cps(expected),
            "rule {rule}: {source:X?}"
        );
    }
}

#[test]
fn unstable_cluster_is_left_as_typed() {
    // Rule 2.3. The SIL oracle differs here (spec O1, O2).
    let cases: &[&[u32]] = &[
        // Sorting would move the stray ZWJ last, next to the next syllable's base.
        &[0x1780, 0x200D, 0x17B6, 0x1781, 0x17C9],
        // Sorting would move the dangling coeng last, next to the next syllable's base.
        &[0x1780, 0x17D2, 0x17CC, 0x1781, 0x17CC],
        // Sorting would put ATTHACAN (ccc 230) before U+0316 (ccc 220), which NFC swaps.
        &[0x1780, 0x17DD, 0x17B6, 0x0316],
    ];
    for &text in cases {
        assert_eq!(normalize(&cps(text)), cps(text), "{text:X?}");
    }
}

#[test]
fn documented_oracle_differences() {
    // Pheasa's side of the spec's "Differences from the oracle".
    let cases: &[(&str, &[u32], &[u32])] = &[
        (
            "O4",
            &[0x179F, 0x17C1, 0x17BB, 0x17B7],
            &[0x179F, 0x17CA, 0x17C1, 0x17B7],
        ),
        (
            "O4",
            &[0x1780, 0x17D2, 0x179A, 0x17D2, 0x1781, 0x17D2, 0x1782],
            &[0x1780, 0x17D2, 0x1781, 0x17D2, 0x1782, 0x17D2, 0x179A],
        ),
        ("O5", &[0x1789, 0x17BB, 0x17B7], &[0x1789, 0x17C9, 0x17B7]),
        ("O6", &[0x179F, 0x17BB, 0x17D0], &[0x179F, 0x17BB, 0x17D0]),
        (
            "O7",
            &[0x1794, 0x17D2, 0x1780, 0x17BB, 0x17B7],
            &[0x1794, 0x17D2, 0x1780, 0x17C9, 0x17B7],
        ),
        (
            "O7",
            &[
                0x1780, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17BB, 0x17B7,
            ],
            &[
                0x1780, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17D2, 0x1798, 0x17CA, 0x17B7,
            ],
        ),
        (
            "O8",
            &[0x179F, 0x17CC, 0x17CC, 0x17D2, 0x179A, 0x17BB, 0x17B9],
            &[0x179F, 0x17CC, 0x17CC, 0x17D2, 0x179A, 0x17BB, 0x17B9],
        ),
    ];
    for &(row, source, ours) in cases {
        assert_eq!(normalize(&cps(source)), cps(ours), "{row}: {source:X?}");
    }
}

#[test]
fn preserve_coeng_da() {
    let text = cps(&[0x1780, 0x17D2, 0x178A, 0x17B6]);
    assert_eq!(normalize(&text), cps(&[0x1780, 0x17D2, 0x178F, 0x17B6]));
    let options = Options {
        preserve_coeng_da: true,
        ..Options::default()
    };
    assert_eq!(normalize_with(&text, options), text);
}

#[test]
fn option_examples() {
    let zwsp = |zwsp| Options {
        zwsp,
        ..Options::default()
    };
    let digits = |digits| Options {
        digits,
        ..Options::default()
    };
    let fold = Options {
        fold_deprecated: true,
        ..Options::default()
    };
    let khmer_digits: Vec<u32> = (0x17E0..=0x17E9).collect();
    let ascii_digits: Vec<u32> = (0x30..=0x39).collect();
    let lek_attak: Vec<u32> = (0x17F0..=0x17F9).collect();
    let examples: &[(Options, &[u32], &[u32])] = &[
        (
            zwsp(Zwsp::Strip),
            &[0x1780, 0x200B, 0x1781],
            &[0x1780, 0x1781],
        ),
        (
            zwsp(Zwsp::Space),
            &[0x1780, 0x200B, 0x1781],
            &[0x1780, 0x20, 0x1781],
        ),
        (digits(Digits::Ascii), &khmer_digits, &ascii_digits),
        (digits(Digits::Khmer), &ascii_digits, &khmer_digits),
        // LEK ATTAK divination numerals are never converted
        (digits(Digits::Ascii), &lek_attak, &lek_attak),
        (fold, &[0x17A3], &[0x17A2]),
        (fold, &[0x17A4], &[0x17A2, 0x17B6]),
        (fold, &[0x17D8], &[0x17D4, 0x179B, 0x17D4]),
        (fold, &[0x1780, 0x17B4, 0x17B6], &[0x1780, 0x17B6]),
        (fold, &[0x1780, 0x17B5], &[0x1780]),
        // Options run before Stage 2: removing ZWSP joins the coeng to its base
        (
            zwsp(Zwsp::Strip),
            &[0x1780, 0x17B6, 0x17D2, 0x200B, 0x1781],
            &[0x1780, 0x17D2, 0x1781, 0x17B6],
        ),
        // ... and before NFC: removing 17B4 exposes <17DD 17D2>, which NFC reorders
        (
            fold,
            &[0x1780, 0x17DD, 0x17B4, 0x17D2, 0x1781],
            &[0x1780, 0x17D2, 0x17DD, 0x1781],
        ),
    ];
    for &(options, source, expected) in examples {
        assert_eq!(
            normalize_with(&cps(source), options),
            cps(expected),
            "{options:?}: {source:X?}"
        );
    }
}

#[test]
fn defaults_keep_zwsp_digits_and_deprecated_characters() {
    let text = "\u{200B}0\u{17E0}\u{17A3}\u{17A4}\u{17B4}\u{17B5}\u{17D8}";
    assert_eq!(normalize(text), text);
}
