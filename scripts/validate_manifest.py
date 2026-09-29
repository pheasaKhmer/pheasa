"""Validate provenance manifests under data/.

Every record in data/**/manifest*.jsonl must state where its text came from,
under which license, when it was retrieved, and how it was transformed.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REQUIRED_FIELDS = ("source", "license", "retrieved", "transform")


def check_record(record: object, where: str) -> list[str]:
    if not isinstance(record, dict):
        return [f"{where}: record is not a JSON object"]
    errors = [
        f"{where}: missing or empty {field!r}" for field in REQUIRED_FIELDS if not record.get(field)
    ]
    retrieved = record.get("retrieved")
    if retrieved:
        try:
            date.fromisoformat(str(retrieved))
        except ValueError:
            errors.append(f"{where}: 'retrieved' is not an ISO date: {retrieved!r}")
    return errors


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / "data").glob("**/manifest*.jsonl")):
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
            errors.extend(check_record(record, where))
    return errors


def main() -> int:
    errors = check(Path.cwd())
    for error in errors:
        print(f"manifest: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
