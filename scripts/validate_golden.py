"""Validate the normalizer's golden fixtures in tests/golden/*.jsonl.

Each record is a real input with the output a native speaker has verified. It must carry
provenance (as in data manifests), a verifier and date, and no personal data. Drafts in
tests/golden/drafts/ are not golden and are not checked.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_manifest import check_record

OPTIONS = {"preserve_coeng_da", "zwsp", "digits", "fold_deprecated"}
ID_PATTERN = re.compile(r"G-\d{4}")
# Handles and email addresses must be removed from fixtures: personal data never goes
# into public test data.
PERSONAL = re.compile(r"(?<![\w.])@\w{2,}|[\w.+-]+@[\w-]+\.[\w.]+")


def check_fixture(record: object, where: str) -> list[str]:
    if not isinstance(record, dict):
        return [f"{where}: record is not a JSON object"]
    errors = check_record(record, where)
    if not ID_PATTERN.fullmatch(str(record.get("id", ""))):
        errors.append(f"{where}: 'id' must look like G-0001")
    for field in ("input", "expected"):
        if not isinstance(record.get(field), str) or not record[field]:
            errors.append(f"{where}: {field!r} must be a non-empty string")
        elif PERSONAL.search(record[field]):
            errors.append(f"{where}: {field!r} looks like it contains a handle or email")
    options = record.get("options", {})
    if not isinstance(options, dict) or not set(options) <= OPTIONS:
        errors.append(f"{where}: 'options' must be an object with keys from {sorted(OPTIONS)}")
    if not record.get("verified_by"):
        errors.append(f"{where}: missing 'verified_by' (golden fixtures are human-verified)")
    try:
        date.fromisoformat(str(record.get("verified_at")))
    except ValueError:
        errors.append(f"{where}: 'verified_at' is not an ISO date")
    return errors


def check(root: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for path in sorted((root / "tests" / "golden").glob("*.jsonl")):
        rel = path.relative_to(root)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            where = f"{rel}:{lineno}"
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{where}: invalid JSON ({exc.msg})")
                continue
            errors.extend(check_fixture(record, where))
            fixture_id = record.get("id") if isinstance(record, dict) else None
            if fixture_id in seen:
                errors.append(f"{where}: duplicate id {fixture_id} (first at {seen[fixture_id]})")
            elif fixture_id:
                seen[fixture_id] = where
    return errors


def main() -> int:
    errors = check(Path.cwd())
    for error in errors:
        print(f"golden: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
