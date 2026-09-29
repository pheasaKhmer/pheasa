"""Keep bench/tasks/versions.lock.json in step with the task prompts.

    uv run python scripts/lock_tasks.py           # update the lock
    uv run python scripts/lock_tasks.py --check   # used by make check

A task's prompt may only change together with its version (project rule: a changed task
spec or prompt needs a version bump and a CHANGELOG entry). Both modes refuse a prompt
change that keeps the old version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

TASKS = Path("bench/tasks")
LOCK = TASKS / "versions.lock.json"


def current() -> dict[str, dict[str, str]]:
    entries = {}
    for path in sorted(TASKS.glob("*.toml")):
        task = tomllib.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(task["prompt"].encode("utf-8")).hexdigest()
        entries[task["name"]] = {"version": task["version"], "prompt_sha256": digest}
    return entries


def problems(locked: dict, now: dict) -> list[str]:
    return [
        f"{name}: prompt changed but version is still {entry['version']}; bump it"
        for name, entry in now.items()
        if name in locked
        and locked[name]["prompt_sha256"] != entry["prompt_sha256"]
        and locked[name]["version"] == entry["version"]
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not TASKS.exists():
        return 0
    locked = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    now = current()
    errors = problems(locked, now)
    if args.check and not errors and locked != now:
        errors.append(f"{LOCK} is out of date: run scripts/lock_tasks.py")
    for error in errors:
        print(f"tasks: {error}", file=sys.stderr)
    if errors or args.check:
        return 1 if errors else 0
    LOCK.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
