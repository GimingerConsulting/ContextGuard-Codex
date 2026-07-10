from __future__ import annotations

import re
from pathlib import Path


HIGH_RISK_TERMS = {
    "auth",
    "authentication",
    "authorization",
    "concurrency",
    "concurrent",
    "credential",
    "data loss",
    "data integrity",
    "database migration",
    "destructive",
    "incident",
    "migration",
    "payment",
    "permission",
    "production",
    "race condition",
    "schema",
    "secret",
    "security",
    "thread-safe",
    "thread safe",
    "transaction",
}

HIGH_RISK_PATH_PARTS = {
    "auth",
    "authentication",
    "concurrency",
    "credential",
    "migration",
    "payment",
    "permission",
    "schema",
    "secret",
    "security",
    "transaction",
}

HIGH_RISK_FILE_NAMES = {
    "support_ticket.md",
    "security.md",
    "openapi.json",
}


def _contains_term(text: str, terms: set[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in sorted(terms) if term in lowered]


def _path_signals(path: str) -> list[str]:
    lowered = path.lower().replace("\\", "/")
    signals: list[str] = []
    name = Path(lowered).name
    if name in HIGH_RISK_FILE_NAMES:
        signals.append(f"risky_file:{name}")
    for part in HIGH_RISK_PATH_PARTS:
        if f"/{part}/" in f"/{lowered}/" or lowered.endswith(f"/{part}.py"):
            signals.append(f"risky_path:{part}")
    if "migration" in name:
        signals.append("risky_path:migration")
    return signals


def assess_risk(
    prompt: str,
    *,
    likely_files: list[str] | None = None,
    supplemental_text: str = "",
) -> dict[str, object]:
    combined = "\n".join(part for part in (prompt, supplemental_text) if part)
    term_hits = _contains_term(combined, HIGH_RISK_TERMS)
    path_hits: list[str] = []
    for item in likely_files or []:
        path_hits.extend(_path_signals(item))
    reasons = sorted(set(term_hits + path_hits))
    locked = bool(reasons)
    return {
        "locked": locked,
        "reasons": reasons,
        "level": "high" if locked else "low",
        "routing_locked": locked,
    }


def render_no_delegation_directive(assessment: dict[str, object]) -> str:
    if not assessment.get("locked"):
        return ""
    reasons = ", ".join(str(item) for item in assessment.get("reasons", [])[:6]) or "high_risk"
    return (
        "ContextGuard routing lock: this task is high-risk "
        f"({reasons}). Do not spawn any subagent or worker. "
        "Do not use full-history forks for delegation. Keep design, migration, concurrency, "
        "payment, security, and data-integrity work on the parent model."
    )