//! Every case in `tests/fixtures/parity.tsv` must give exactly the Python output.
//!
//! The file is written by `scripts/export_rust_fixtures.py` from the Python
//! implementation, and `make validate` checks that it is up to date. Its header describes
//! the format.

use std::collections::HashMap;
use std::fmt::Write as _;
use std::path::PathBuf;

use pheasa::{Digits, NORMALIZATION_VERSION, Options, Zwsp, normalize, normalize_with};
use unicode_normalization::UnicodeNormalization;

const ZWSP_VALUES: [Zwsp; 3] = [Zwsp::Keep, Zwsp::Strip, Zwsp::Space];
const DIGIT_VALUES: [Digits; 3] = [Digits::Keep, Digits::Khmer, Digits::Ascii];

struct Case {
    line: usize,
    section: String,
    input: String,
    /// Output with default options.
    default: String,
    /// Output for other option codes, where it differs from `default`.
    others: HashMap<String, String>,
}

struct Fixture {
    /// The `normalization_version` in the header.
    version: Option<String>,
    cases: Vec<Case>,
}

fn unescape(field: &str) -> String {
    let mut out = String::with_capacity(field.len());
    let mut chars = field.chars();
    while let Some(ch) = chars.next() {
        if ch != '\\' {
            out.push(ch);
            continue;
        }
        match chars.next() {
            Some('\\') => out.push('\\'),
            Some('t') => out.push('\t'),
            Some('n') => out.push('\n'),
            Some('r') => out.push('\r'),
            Some('=') => out.push('='),
            Some('u') => {
                let hex: String = chars.by_ref().take_while(|&c| c != '}').collect();
                let hex = hex.strip_prefix('{').expect("\\u{...} escape");
                let code = u32::from_str_radix(hex, 16).expect("hexadecimal escape");
                out.push(char::from_u32(code).expect("escape is a scalar value"));
            }
            other => panic!("unknown escape \\{other:?} in {field:?}"),
        }
    }
    out
}

fn load() -> Fixture {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/parity.tsv");
    let text = std::fs::read_to_string(&path).expect("parity fixture");
    let mut version = None;
    let mut cases = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if let Some(comment) = line.strip_prefix('#') {
            if let Some(value) = comment.trim().strip_prefix("normalization_version:") {
                version = Some(value.trim().to_owned());
            }
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        assert!(
            fields.len() >= 3 && fields.len() % 2 == 1,
            "line {}: malformed case",
            index + 1
        );
        let input = unescape(fields[1]);
        let output = |field: &str| {
            if field == "=" {
                input.clone()
            } else {
                unescape(field)
            }
        };
        let others = fields[3..]
            .chunks(2)
            .map(|pair| (pair[0].to_owned(), output(pair[1])))
            .collect();
        cases.push(Case {
            line: index + 1,
            section: fields[0].to_owned(),
            default: output(fields[2]),
            input,
            others,
        });
    }
    Fixture { version, cases }
}

/// The option code of the fixture: zwsp, digits, `fold_deprecated`, `preserve_coeng_da`.
fn code(options: Options) -> String {
    let zwsp = ZWSP_VALUES.iter().position(|&v| v == options.zwsp).unwrap();
    let digits = DIGIT_VALUES
        .iter()
        .position(|&v| v == options.digits)
        .unwrap();
    format!(
        "{zwsp}{digits}{}{}",
        u8::from(options.fold_deprecated),
        u8::from(options.preserve_coeng_da)
    )
}

/// `options` with every option whose characters do not occur in `input` reset to its
/// default. The fixture stores outputs only for these combinations: the Stage 4 options
/// replace single characters, and rule 3.8 needs U+17D2 and U+178A.
fn project(options: Options, input: &str) -> Options {
    let has = |pred: fn(char) -> bool| input.chars().any(pred);
    let digits = match options.digits {
        Digits::Khmer if has(|c| c.is_ascii_digit()) => Digits::Khmer,
        Digits::Ascii if has(|c| matches!(c, '\u{17E0}'..='\u{17E9}')) => Digits::Ascii,
        _ => Digits::Keep,
    };
    Options {
        zwsp: if input.contains('\u{200B}') {
            options.zwsp
        } else {
            Zwsp::Keep
        },
        digits,
        fold_deprecated: options.fold_deprecated
            && has(|c| {
                matches!(
                    c,
                    '\u{17A3}' | '\u{17A4}' | '\u{17B4}' | '\u{17B5}' | '\u{17D8}'
                )
            }),
        preserve_coeng_da: options.preserve_coeng_da
            && input.contains('\u{17D2}')
            && input.contains('\u{178A}'),
    }
}

fn all_options() -> impl Iterator<Item = Options> {
    ZWSP_VALUES.into_iter().flat_map(|zwsp| {
        DIGIT_VALUES.into_iter().flat_map(move |digits| {
            [false, true].into_iter().flat_map(move |fold_deprecated| {
                [false, true]
                    .into_iter()
                    .map(move |preserve_coeng_da| Options {
                        preserve_coeng_da,
                        zwsp,
                        digits,
                        fold_deprecated,
                    })
            })
        })
    })
}

fn code_points(text: &str) -> String {
    let points: Vec<String> = text
        .chars()
        .map(|c| format!("{:04X}", u32::from(c)))
        .collect();
    points.join(" ")
}

#[test]
fn fixture_matches_this_normalization_version() {
    assert_eq!(load().version.as_deref(), Some(NORMALIZATION_VERSION));
}

#[test]
fn fixture_covers_every_section() {
    let cases = load().cases;
    assert!(cases.len() >= 20_000, "only {} cases", cases.len());
    for section in ["g", "c", "k", "m", "w", "u", "o", "t", "s", "b"] {
        assert!(
            cases.iter().any(|case| case.section == section),
            "no cases in section {section}"
        );
    }
}

#[test]
fn every_case_matches_python_under_every_option_combination() {
    let cases = load().cases;
    let mut checked = 0;
    let mut mismatches = Vec::new();
    for case in &cases {
        let got = normalize(&case.input);
        if got != case.default {
            mismatches.push((case, "normalize".to_owned(), &case.default, got));
        }
        for options in all_options() {
            let projected = code(project(options, &case.input));
            let expected = case.others.get(&projected).unwrap_or(&case.default);
            let got = normalize_with(&case.input, options);
            checked += 1;
            if got != *expected {
                mismatches.push((case, code(options), expected, got));
            }
        }
    }
    let mut report = String::new();
    for (case, options, expected, got) in mismatches.iter().take(20) {
        let _ = writeln!(
            report,
            "line {} [{}] options {options}: input {}\n  want {}\n  got  {}",
            case.line,
            case.section,
            code_points(&case.input),
            code_points(expected),
            code_points(got),
        );
    }
    assert!(
        mismatches.is_empty(),
        "{} of {checked} differ:\n{report}",
        mismatches.len()
    );
}

#[test]
fn every_option_code_in_the_fixture_is_a_projection() {
    // Guards the test above: an output stored under a code that `project` never produces
    // would not be checked.
    for case in load().cases {
        for stored in case.others.keys() {
            let reachable = all_options().any(|o| code(project(o, &case.input)) == *stored);
            assert!(reachable, "line {}: code {stored}", case.line);
        }
    }
}

#[test]
fn outputs_are_idempotent_and_nfc() {
    // Spec test requirements 2 and 3, on the expected outputs.
    for case in load().cases {
        let once = &case.default;
        assert_eq!(normalize(once), *once, "line {}", case.line);
        assert_eq!(once.nfc().collect::<String>(), *once, "line {}", case.line);
    }
}

#[test]
fn unescape_reverses_the_exporter() {
    assert_eq!(unescape(r"a\tb\\c\=\u{0085}\n"), "a\tb\\c=\u{85}\n");
}
