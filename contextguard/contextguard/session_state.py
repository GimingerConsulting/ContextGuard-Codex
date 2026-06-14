from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import state_dir


STATE_VERSION = 1
CHECKPOINT_FIELDS = (
    "current_objective",
    "likely_relevant_files",
    "likely_relevant_symbols",
    "changed_files",
    "verified_tests",
    "known_failures",
    "active_constraints",
    "next_action",
)


def _session_path(root: Path) -> Path:
    return state_dir(root) / "sessions" / "state.json"


def _checkpoint_path(root: Path) -> Path:
    return state_dir(root) / "sessions" / "latest.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _empty_state(checkpoint: dict | None = None) -> dict:
    return {
        "version": STATE_VERSION,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": checkpoint or {},
        "commands": [],
        "reads": {},
        "evidence": {},
        "advice_emitted": [],
        "metrics": {"repeated_reads_detected": 0, "budget_advice_emitted": 0},
    }


def load_session_state(root: Path) -> dict:
    path = _session_path(root)
    if not path.exists():
        return _empty_state(load_checkpoint(root))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state(load_checkpoint(root))
    if data.get("version") != STATE_VERSION:
        return _empty_state(load_checkpoint(root))
    return data


def save_session_state(root: Path, state: dict) -> Path:
    path = _session_path(root)
    _write_json(path, state)
    return path


def reset_session_state(root: Path) -> Path:
    checkpoint = load_session_state(root).get("checkpoint") or load_checkpoint(root)
    return save_session_state(root, _empty_state(checkpoint))


def load_checkpoint(root: Path) -> dict:
    path = _checkpoint_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def persist_checkpoint(root: Path, facts: dict) -> dict:
    compact = {key: facts[key] for key in CHECKPOINT_FIELDS if facts.get(key)}
    compact.update(
        {
            "version": STATE_VERSION,
            "checkpoint_id": uuid.uuid4().hex[:12],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_json(_checkpoint_path(root), compact)
    state = load_session_state(root)
    state["checkpoint"] = compact
    save_session_state(root, state)
    return compact


def record_evidence(root: Path, fingerprint: str, summary_path: str) -> dict:
    state = load_session_state(root)
    evidence = state.setdefault("evidence", {})
    existing = evidence.get(fingerprint)
    if existing:
        existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
        save_session_state(root, state)
        return {
            "repeated": True,
            "occurrences": existing["occurrences"],
            "first_summary_path": existing["first_summary_path"],
        }
    evidence[fingerprint] = {
        "occurrences": 1,
        "first_summary_path": summary_path,
    }
    save_session_state(root, state)
    return {"repeated": False, "occurrences": 1, "first_summary_path": summary_path}
