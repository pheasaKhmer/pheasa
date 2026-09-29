# Test oracle: SIL `khnormal`

`khnormal_sil.py` is an unmodified copy of SIL's reference implementation of the
Khmer encoding structure described in Unicode Technical Note #61. It is used **only in
tests**, to check Pheasa's normalizer against the reference behavior (see
`spec/normalization.md` and decision D-007). It is not shipped in the `pheasa`
package.

| Field | Value |
|---|---|
| Source | https://github.com/sillsdev/khmer-character-specification |
| Path | `python/scripts/khnormal` |
| Commit | `08ae0374c080b33a9e4264af7bff2501bfe365d7` (2025-03-14) |
| SHA-256 | `3cf799b41e09bea3603f5c4c5c7c5faf951d744fe0249bc90a0020126ad91e6d` |
| License | MIT (see `LICENSE` in this directory) |
| Retrieved | 2026-09-30 |

Only this MIT-licensed script is vendored. The rest of that repository (the
specification text and word lists) is licensed CC BY-NC-SA 4.0 and is not included.

Do not edit `khnormal_sil.py`. To update it, replace the file with a newer upstream
version and update the commit and hash above.
