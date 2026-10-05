# pheasa (Rust)

The Khmer text normalizer of [Pheasa](https://github.com/pheasaKhmer/pheasa), ported to
Rust for places where Python is not available, such as keyboards on phones. It gives
the same output as the Python package's `pheasa.normalize` for every input and option.

```rust
use pheasa::{Digits, Options, normalize, normalize_with};

// U+1781 U+17C2 U+17D2 U+1798 U+179A becomes U+1781 U+17D2 U+1798 U+17C2 U+179A.
assert_eq!(normalize("ខែ្មរ"), "ខ្មែរ");

let options = Options { digits: Digits::Ascii, ..Options::default() };
assert_eq!(normalize_with("១២៣", options), "123");
```

`normalize` puts every Khmer syllable into the order defined by Unicode Technical Note
#61 and replaces "do not use" sequences with their preferred equivalents. The rules are
specified in
[`spec/normalization.md`](https://github.com/pheasaKhmer/pheasa/blob/main/spec/normalization.md),
and the [user guide](https://github.com/pheasaKhmer/pheasa/blob/main/docs/normalizer.md)
explains them.

The options are the Python keyword arguments, all off by default:

| Python | Rust (`Options` field) |
|---|---|
| `zwsp="keep"`, `"strip"`, `"space"` | `zwsp: Zwsp::Keep`, `Zwsp::Strip`, `Zwsp::Space` |
| `digits="keep"`, `"khmer"`, `"ascii"` | `digits: Digits::Keep`, `Digits::Khmer`, `Digits::Ascii` |
| `fold_deprecated=True` | `fold_deprecated: true` |
| `preserve_coeng_da=True` | `preserve_coeng_da: true` |

## Same output as Python

The Python implementation is the reference, and `NORMALIZATION_VERSION` (`"1"`) names
the output of both. The tests require identical output on 24,040 inputs, each under all
36 combinations of options: every golden fixture, every Khmer character in a few
contexts, and text generated from the alphabets of the Python property tests. The cases
are written from the Python implementation by `scripts/export_rust_fixtures.py`
(decision D-015 in
[`DECISIONS.md`](https://github.com/pheasaKhmer/pheasa/blob/main/DECISIONS.md)).

NFC of non-Khmer text uses the Unicode data of the `unicode-normalization` crate
(Unicode 17.0.0, pinned), while Python uses its interpreter's. They agree on every
character assigned in both Unicode versions.

Not ported yet: `normalize(text, report=True)`, which lists every change with offsets,
and `pheasa.validate`.

## Install

Until the crate is published on crates.io, depend on it through git, pinned to a
commit:

```toml
[dependencies]
pheasa = { git = "https://github.com/pheasaKhmer/pheasa", rev = "<commit>" }
```

Cargo finds the crate in the `rust/` directory of the repository.

## Development

```bash
cd rust
cargo test
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

`rust-toolchain.toml` pins the Rust version. The parity cases are regenerated from the
repository root with `uv run python scripts/export_rust_fixtures.py`, after new golden
fixtures or a rule change (which also needs a new `NORMALIZATION_VERSION`). `make check`
fails while they are out of date.

## License

[Apache-2.0](https://github.com/pheasaKhmer/pheasa/blob/main/LICENSE).

---

Created and maintained by **Samputhy Khim** ([@organi-cs](https://github.com/organi-cs), [ORCID 0009-0008-4510-8839](https://orcid.org/0009-0008-4510-8839)).
