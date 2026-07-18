from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import state_dir


STATE_VERSION = 2
MAX_COMMANDS = 200
MAX_READS = 200
MAX_EVIDENCE = 200
MAX_OUTPUTS = 200
MAX_ROUTING_EVENTS = 100
MAX_LEDGER_EVENTS = 500
CHECKPOINT_FIELDS = (
    "current_objective",
    "likely_relevant_files",
    "likely_relevant_symbols",
    "changed_files",
    "verified_tests",
    "known_failures",
    "active_constraints",
    "next_action",
    "integration_points",
    "verified_facts",
    "rejected_hypotheses",
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
        "outputs": {},
        "routing_events": [],
        "advice_emitted": [],
        "metrics": {
            "repeated_reads_detected": 0,
            "budget_advice_emitted": 0,
            "routed_workers_started": 0,
            "routed_workers_completed": 0,
        },
        "routing_locked": False,
        "routing_lock_reasons": [],
        "host": "codex",
        "ledger": {},
        "ledger_totals": {
            "bytes_added": 0,
            "bytes_saved": 0,
            "tokens_added": 0,
            "tokens_saved": 0,
        },
        "ledger_events": [],
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
    state["commands"] = list(state.get("commands", []))[-MAX_COMMANDS:]
    state["routing_events"] = list(state.get("routing_events", []))[-MAX_ROUTING_EVENTS:]
    state["ledger_events"] = list(state.get("ledger_events", []))[-MAX_LEDGER_EVENTS:]
    for key, limit in (("reads", MAX_READS), ("evidence", MAX_EVIDENCE), ("outputs", MAX_OUTPUTS)):
        values = state.get(key, {})
        if isinstance(values, dict) and len(values) > limit:
            state[key] = dict(list(values.items())[-limit:])
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


def _checkpoint_value(value: object) -> bool:
    return value not in (None, "", [], {}, ())


def persist_checkpoint(root: Path, facts: dict) -> dict:
    existing = load_checkpoint(root)
    compact = {}
    for key in CHECKPOINT_FIELDS:
        if key in facts:
            new_value = facts[key]
            if _checkpoint_value(new_value):
                compact[key] = new_value
            continue
        existing_value = existing.get(key)
        if _checkpoint_value(existing_value):
            compact[key] = existing_value
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


def record_evidence(
    root: Path,
    fingerprint: str,
    summary_path: str,
    *,
    locations: list[str] | None = None,
    failed_tests: list[str] | None = None,
) -> dict:
    state = load_session_state(root)
    evidence = state.setdefault("evidence", {})
    existing = evidence.get(fingerprint)
    if existing:
        existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
        existing["last_summary_path"] = summary_path
        if locations:
            existing["locations"] = locations[:8]
        if failed_tests:
            existing["failed_tests"] = failed_tests[:8]
        save_session_state(root, state)
        return {
            "repeated": True,
            "occurrences": existing["occurrences"],
            "first_summary_path": existing["first_summary_path"],
            "locations": existing.get("locations", []),
        }
    evidence[fingerprint] = {
        "occurrences": 1,
        "first_summary_path": summary_path,
        "last_summary_path": summary_path,
        "locations": (locations or [])[:8],
        "failed_tests": (failed_tests or [])[:8],
    }
    save_session_state(root, state)
    return {
        "repeated": False,
        "occurrences": 1,
        "first_summary_path": summary_path,
        "locations": evidence[fingerprint]["locations"],
    }


def record_output(
    root: Path,
    fingerprint: str,
    summary_path: str,
    *,
    raw_bytes: int,
) -> dict:
    """Record an exact, session-local output hash for reversible deduplication."""
    state = load_session_state(root)
    outputs = state.setdefault("outputs", {})
    existing = outputs.get(fingerprint)
    if existing:
        existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
        existing["last_summary_path"] = summary_path
        save_session_state(root, state)
        return {
            "repeated": True,
            "occurrences": existing["occurrences"],
            "first_summary_path": existing["first_summary_path"],
            "reference": fingerprint[:12],
        }
    outputs[fingerprint] = {
        "occurrences": 1,
        "first_summary_path": summary_path,
        "last_summary_path": summary_path,
        "raw_bytes": raw_bytes,
    }
    save_session_state(root, state)
    return {
        "repeated": False,
        "occurrences": 1,
        "first_summary_path": summary_path,
        "reference": fingerprint[:12],
    }


def set_routing_lock(root: Path, locked: bool, *, reasons: list[str] | None = None) -> None:
    state = load_session_state(root)
    state["routing_locked"] = locked
    state["routing_lock_reasons"] = list(reasons or [])
    save_session_state(root, state)


def record_routing_event(root: Path, event: dict) -> None:
    state = load_session_state(root)
    state.setdefault("routing_events", []).append(event)
    metrics = state.setdefault("metrics", {})
    if event.get("event") == "start" and event.get("agent_type") == "contextguard-worker":
        metrics["routed_workers_started"] = int(metrics.get("routed_workers_started", 0)) + 1
    if (
        event.get("event") == "stop"
        and event.get("agent_type") == "contextguard-worker"
        and event.get("status") == "completed"
    ):
        metrics["routed_workers_completed"] = int(metrics.get("routed_workers_completed", 0)) + 1
    save_session_state(root, state)
