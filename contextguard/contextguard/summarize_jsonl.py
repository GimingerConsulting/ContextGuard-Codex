from __future__ import annotations

import json
from pathlib import Path


def summarize(path: Path, limit: int = 5) -> dict:
    keys: set[str] = set()
    samples = []
    count = 0
    invalid_records = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        lines = handle
        for line in lines:
            if not line.strip():
                continue
            count += 1
            if len(samples) < limit:
                samples.append(line[:300].rstrip())
            try:
                value = json.loads(line)
            except Exception:
                invalid_records += 1
                continue
            if isinstance(value, dict):
                keys.update(value)
    return {
        "file": path.as_posix(),
        "records": count,
        "invalid_records": invalid_records,
        "observed_keys": sorted(keys)[:100],
        "samples": samples,
    }
