from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import state_dir
from .session_state import CHECKPOINT_FIELDS, load_checkpoint, load_session_state


def _prior_path(root: Path) -> Path:
    return state_dir(root) / "sessions" / "prior.json"


def persist_cross_session_summary(root: Path) -> dict[str, object]:
    checkpoint = load_checkpoint(root)
    state = load_session_state(root)
    summary = {
        "version": 1,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": {key: checkpoint[key] for key in CHECKPOINT_FIELDS if checkpoint.get(key)},
        "verified_reads": list((state.get("reads") or {}).keys())[:20],
        "evidence_fingerprints": list((state.get("evidence") or {}).keys())[:20],
        "command_families": sorted({item.get("family") for item in state.get("commands", []) if item.get("family")}),
    }
    path = _prior_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def load_cross_session_summary(root: Path) -> dict[str, object]:
    path = _prior_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def render_cross_session_brief(root: Path, *, token_limit: int = 250) -> str:
    summary = load_cross_session_summary(root)
    if not summary:
        return ""
    checkpoint = summary.get("checkpoint") or {}
    lines = ["ContextGuard prior-session resume:"]
    objective = checkpoint.get("current_objective")
    if objective:
        lines.append(f"- objective: {objective}")
    files = checkpoint.get("likely_relevant_files") or []
    if files:
        lines.append("- likely_files: " + ", ".join(files[:4]))
    tests = checkpoint.get("verified_tests") or []
    if tests:
        lines.append("- verified_tests: " + ", ".join(tests[:3]))
    failures = checkpoint.get("known_failures") or []
    if failures:
        lines.append("- known_failures: " + ", ".join(failures[:3]))
    families = summary.get("command_families") or []
    if families:
        lines.append("- prior_command_families: " + ", ".join(families[:5]))
    evidence = summary.get("evidence_fingerprints") or []
    if evidence:
        lines.append(f"- prior_evidence_entries: {len(evidence)} (reuse expand/inspect before re-reading logs)")
    reads = summary.get("verified_reads") or []
    if reads:
        lines.append(f"- prior_verified_reads: {len(reads)}")
    text = "\n".join(lines)
    while len(text) > token_limit * 4 and len(lines) > 1:
        lines.pop()
        text = "\n".join(lines)
    return text