"""Permanent cache of raw model responses, so that rerunning never pays twice.

Keyed by (model, task, task version, prompt hash, generation parameters), as the project
requires. Entries never expire; delete the directory to start over.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

__all__ = ["ResponseCache", "cache_key"]


def cache_key(model: str, task: str, version: str, prompt: str, params: dict) -> str:
    fields = {
        "model": model,
        "task": task,
        "task_version": version,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "params": params,
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def put(self, key: str, entry: dict) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entry, ensure_ascii=False, sort_keys=True), encoding="utf-8")
