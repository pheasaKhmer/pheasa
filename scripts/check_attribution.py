"""Fail if a public artifact is missing the author credit."""

from __future__ import annotations

import sys
from pathlib import Path

AUTHOR = "Samputhy Khim"

# Files that must always exist and credit the author.
REQUIRED = ["README.md", "CITATION.cff", "pyproject.toml"]

# Public artifacts that must credit the author whenever they exist.
OPTIONAL_GLOBS = [
    "site/**/*.html",
    "hf/**/README.md",
    "paper/**/*.tex",
    "rust/README.md",
    "rust/Cargo.toml",
]


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED:
        path = root / name
        if not path.is_file():
            errors.append(f"{name}: missing")
        elif AUTHOR not in path.read_text(encoding="utf-8"):
            errors.append(f"{name}: does not credit {AUTHOR!r}")

    # CITATION.cff stores the name split into family and given parts.
    cff = root / "CITATION.cff"
    if cff.is_file():
        text = cff.read_text(encoding="utf-8")
        if "family-names: Khim" in text and "given-names: Samputhy" in text:
            errors = [e for e in errors if not e.startswith("CITATION.cff: does not credit")]

    for pattern in OPTIONAL_GLOBS:
        for path in sorted(root.glob(pattern)):
            if AUTHOR not in path.read_text(encoding="utf-8"):
                errors.append(f"{path.relative_to(root)}: does not credit {AUTHOR!r}")
    return errors


def main() -> int:
    errors = check(Path.cwd())
    for error in errors:
        print(f"attribution: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
