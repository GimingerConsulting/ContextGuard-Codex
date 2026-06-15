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
    return f"""ContextGuard policy: {POLICY_NAME}.

- Orient once; Reuse unchanged reads; group repeated inspection; inspect files or symbols.
- For tests, linters, builds; recursive listings or searches; `git diff`; or structured data or logs, run `.contextguard/bin/contextguard capture -- <command>` before stdout reaches Codex (`sh -lc`). This protects non-interactive runs and does not depend on lifecycle hook dispatch.
- Never run `sed`, `tail`, `head`, `cat`, `awk`, `jq`, or `rg` directly on logs, artifacts, structured/generated output, or multiple files. Pipelines do not make output safe; capture the complete pipeline. Small, bounded source reads of one file may run directly.
- Prefer `contextguard inspect` for 2-4 named source files when one bounded tool call can replace repeated reads.
- Prefer one failed test before a full suite. Reuse passing validation until relevant code changes.
- Escalate only the missing evidence from the archived output; do not disable protection task-wide.
- Adaptive routing: Before any delegation, scan the task for the risk terms below. For security, auth, migrations, schemas, payments, concurrency, destructive or production operations, secrets, transactions, or data integrity, do not spawn any subagent. Otherwise use exactly one bounded implementation worker `contextguard-worker` only for nontrivial scope. Start with an isolated prompt, never a full-history fork. The parent model must review the diff and final-validate; fall back locally on ambiguity or failure.
- Do not narrate routine inspection or tool use, restate intent, echo source, or print unasked diffs.
- Final responses: changed files, validation, and only real risks.
- Never trade correctness, context, validation, security, or data integrity for brevity.

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
    if len(text.split()) > 180:
        violations.append("excessive_length")
    if re.search(r"^diff --git ", text, re.MULTILINE):
        violations.append("full_diff_echo")
    fenced_lines = sum(1 for line in text.splitlines() if line.startswith("```"))
    if fenced_lines >= 2 and len(text.splitlines()) > 80:
        violations.append("source_file_echo")
    return {"valid": not violations, "violations": violations}
