from __future__ import annotations

import json
from pathlib import Path

from .config import state_dir
from .session_state import persist_checkpoint
from .task_classifier import classify_task
from .utils import estimate_tokens


def build_capsule(root: Path, prompt: str, token_limit: int = 400) -> str:
    result = classify_task(root, prompt)
    if result["confidence"] == "low":
        text = (
            "ContextGuard task capsule: low classification confidence. "
            "Start with targeted search, symbol/range inspection and automatic context escalation when needed."
        )
        return text

    for file_limit, symbol_limit, test_limit in ((4, 2, 3), (3, 1, 2), (2, 1, 1), (1, 0, 0)):
        files = ", ".join(result["likely_files"][:file_limit]) or "none"
        symbols = ", ".join(
            f"{item['name']}@{item['path']}:{item['line']}"
            for item in result.get("likely_symbols", [])[:symbol_limit]
        ) or "none"
        tests = ", ".join(result.get("relevant_tests", [])[:test_limit]) or "none"
        text = (
            "ContextGuard capsule: "
            f"confidence={result['confidence']}; files={files}; symbols={symbols}; tests={tests}; "
            "start scoped; expand if needed."
        )
        if estimate_tokens(text) <= token_limit:
            return text
    return "ContextGuard capsule: start scoped; expand only when evidence is insufficient."


# Preserve the execution frontier before broader discovery context.  When the
# capsule must shrink, trimming from the tail keeps the next atomic action and
# already-verified state available after compaction.
SESSION_FIELDS = (
    "current_objective",
    "next_action",
    "changed_files",
    "likely_relevant_symbols",
    "verified_tests",
    "known_failures",
    "active_constraints",
    "likely_relevant_files",
    "integration_points",
    "verified_facts",
    "rejected_hypotheses",
)


def _render_session_value(value: object) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={value[key]}" for key in sorted(value))
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def persist_session_capsule(root: Path, facts: dict) -> Path:
    persist_checkpoint(root, facts)
    return state_dir(root) / "sessions" / "latest.json"


def build_session_capsule(root: Path, token_limit: int = 400) -> str:
    path = state_dir(root) / "sessions" / "latest.json"
    if not path.exists():
        return ""
    try:
        facts = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    parts = []
    for key in SESSION_FIELDS:
        value = facts.get(key)
        if not value:
            continue
        rendered = _render_session_value(value)
        parts.append(f"{key}={rendered}")
    text = "ContextGuard resume capsule: " + "; ".join(parts)
    while estimate_tokens(text) > token_limit and parts:
        parts.pop()
        text = "ContextGuard resume capsule: " + "; ".join(parts)
    return text if parts else ""
