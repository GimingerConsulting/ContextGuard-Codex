from __future__ import annotations

import re


POLICY_NAME = "Adaptive Maximum Efficiency"


def classify_complexity(prompt: str, *, changed_file_count: int = 0) -> str:
    lowered = prompt.lower()
    if any(term in lowered for term in ("architecture", "migration", "schema", "persistent", "security")):
        return "architectural"
    if changed_file_count >= 5 or any(term in lowered for term in ("cross-module", "benchmark", "refactor")):
        return "complex"
    if changed_file_count <= 1 and len(prompt.split()) <= 5:
        return "trivial"
    if changed_file_count <= 2:
        return "small"
    return "medium"


def render_policy(project_kind: str) -> str:
    orientation = (
        "- Empty/greenfield repo: implement directly; ContextGuard stays passive."
        if project_kind == "empty"
        else (
            "- The first prompt already includes a bounded task evidence packet; "
            "use it to skip broad orientation and inspect only evidence still needed."
        )
    )
    return f"""ContextGuard policy: {POLICY_NAME}.

{orientation}
- Use normal shell/source commands. Hooks optimize large output automatically; never call ContextGuard commands, help, brief, or archives yourself.
- Read exact source once and reuse it. Batch independent reads and searches in one call.
- After editing, combine targeted tests, the full suite, and the diff check in one validation call when safe; reuse passing evidence.
- Do not scan `.contextguard`, generated docs, caches, or archives.
- Preserve correctness, security, validation, and data integrity. Work locally unless delegation clearly saves calls.
- Stop once evidence is sufficient. Keep reasoning concise; final: changed files, validation, and real risks.

Project: {project_kind}.
"""


def inspect_final_response(
    text: str,
    *,
    changed_files: list[str] | None = None,
    validation_required: bool = False,
    risk_required: bool = False,
    detailed_requested: bool = False,
) -> dict[str, object]:
    if detailed_requested:
        return {"valid": True, "violations": []}
    lowered = text.lower()
    violations: list[str] = []
    if changed_files and not any(path.lower() in lowered for path in changed_files):
        violations.append("missing_changed_file")
    if validation_required and not re.search(r"\b(test|tests|validation|verified|check|checks)\b", lowered):
        violations.append("missing_validation")
    if risk_required and not re.search(r"\b(risk|limitation|unverified|blocker)\b", lowered):
        violations.append("missing_risk")
    if "if you want" in lowered or "i can also" in lowered:
        violations.append("unrelated_follow_up")
    if "you asked me to" in lowered or "your request was" in lowered:
        violations.append("task_restatement")
    if any(phrase in lowered for phrase in ("i'll inspect", "i will inspect", "next i'll run", "now i'll run")):
        violations.append("routine_narration")
    if len(text.split()) > 140:
        violations.append("excessive_length")
    if re.search(r"^diff --git ", text, re.MULTILINE):
        violations.append("full_diff_echo")
    fenced_lines = sum(1 for line in text.splitlines() if line.startswith("```"))
    if fenced_lines >= 2 and len(text.splitlines()) > 80:
        violations.append("source_file_echo")
    return {"valid": not violations, "violations": violations}
