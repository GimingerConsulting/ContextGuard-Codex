from __future__ import annotations

import json
from pathlib import Path

from .config import state_dir


def record_archive_metadata(root: Path, *, archive_path: str, fingerprint: str, raw_bytes: int) -> None:
    path = state_dir(root) / "sessions" / "archive_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"entries": []}
    except (OSError, json.JSONDecodeError):
        data = {"entries": []}
    entries = data.setdefault("entries", [])
    existing = next((item for item in entries if item.get("fingerprint") == fingerprint), None)
    if existing:
        existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
        existing["last_archive_path"] = archive_path
    else:
        entries.append(
            {
                "fingerprint": fingerprint,
                "occurrences": 1,
                "raw_bytes": raw_bytes,
                "first_archive_path": archive_path,
                "last_archive_path": archive_path,
            }
        )
    data["entries"] = entries[-200:]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def archive_index_summary(root: Path) -> dict[str, object]:
    path = state_dir(root) / "sessions" / "archive_index.json"
    if not path.exists():
        return {"entries": 0, "repeated_fingerprints": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"entries": 0, "repeated_fingerprints": 0}
    entries = data.get("entries") or []
    repeated = sum(1 for item in entries if int(item.get("occurrences", 1)) > 1)
    return {"entries": len(entries), "repeated_fingerprints": repeated}