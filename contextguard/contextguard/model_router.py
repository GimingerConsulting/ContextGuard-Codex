from __future__ import annotations

import re
from pathlib import Path

from .risk_assessment import assess_risk, render_no_delegation_directive
from .session_state import set_routing_lock


WORKER_AGENT = "contextguard-worker"
WORKER_MODEL = "gpt-5.4-mini"

IMPLEMENTATION_TERMS = {
    "add", "build", "change", "fix", "implement", "refactor", "support", "update",
}


def _contains_term(prompt: str, terms: set[str]) -> bool:
    lowered = prompt.lower()
    return any(term in lowered for term in terms)


def route_task(
    root: Path,
    prompt: str,
    *,
    likely_files: list[str],
    confidence: str,
    supplemental_text: str = "",
) -> dict[str, object]:
    words = re.findall(r"[A-Za-z0-9_.-]+", prompt)
    assessment = assess_risk(prompt, likely_files=likely_files, supplemental_text=supplemental_text)
    base = {
        "agent": WORKER_AGENT,
        "model": WORKER_MODEL,
        "reasoning_effort": "medium",
        "max_workers": 1,
        "parent_responsibilities": ["planning", "risk decisions", "diff review", "final validation"],
        "risk": assessment,
    }
    if assessment["locked"]:
        set_routing_lock(root, True, reasons=list(assessment.get("reasons", [])))
        return {
            **base,
            "eligible": False,
            "reason": "high_risk_task",
            "directive": render_no_delegation_directive(assessment),
        }
    set_routing_lock(root, False, reasons=[])
    if len(words) <= 5 and len(likely_files) <= 1:
        return {
            **base,
            "eligible": False,
            "reason": "handoff_overhead_exceeds_expected_savings",
            "directive": "",
        }
    if confidence != "high" or not likely_files:
        return {**base, "eligible": False, "reason": "insufficient_scope_confidence", "directive": ""}
    if not _contains_term(prompt, IMPLEMENTATION_TERMS):
        return {**base, "eligible": False, "reason": "not_an_implementation_task", "directive": ""}
    files = ", ".join(likely_files[:4])
    directive = (
        f"ContextGuard routing: delegate exactly one `{WORKER_AGENT}` after orientation with a bounded isolated "
        f"prompt, not a full-history fork. Scope: {files}. Give acceptance criteria and focused tests. Parent must "
        "review the worker diff, run final validation, and continue locally on failure or ambiguity."
    )
    return {**base, "eligible": True, "reason": "bounded_implementation", "directive": directive}
