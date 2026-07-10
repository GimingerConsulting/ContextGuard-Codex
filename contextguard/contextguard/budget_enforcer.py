from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from .optimization_advisor import _family, _read_paths, _snapshot, parts_read_like
from .session_state import load_session_state


LOG_SUFFIXES = {".log", ".jsonl", ".json", ".csv", ".tsv", ".sql"}


@dataclass(frozen=True)
class BudgetDecision:
    action: str
    reason: str
    alternative: str = ""


def _command_key_parts(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _targets_log_or_structured(command: str, root: Path) -> bool:
    for path in _read_paths(root, command):
        if path.suffix.lower() in LOG_SUFFIXES:
            return True
        rel = path.as_posix().lower()
        if any(part in rel for part in ("log", "artifact", "tmp/", ".contextguard/tmp/")):
            return True
    parts = _command_key_parts(command)
    return any(part.endswith(tuple(LOG_SUFFIXES)) for part in parts[1:])


def _source_files_for_inspect(command: str, root: Path) -> list[str]:
    paths = _read_paths(root, command)
    source = []
    for path in paths:
        if path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".md"}:
            try:
                source.append(path.relative_to(root.resolve()).as_posix())
            except ValueError:
                continue
    return source


def _bypasses_capture_runner(command: str) -> bool:
    lowered = command.lower()
    if "contextguard capture" in lowered or ".contextguard/bin/contextguard capture" in lowered:
        return False
    parts = _command_key_parts(command)
    if not parts:
        return False
    if parts[0] in {"tail", "head", "sed", "cat", "awk"}:
        joined = " ".join(parts)
        if any(marker in joined for marker in (".log", ".jsonl", ".contextguard/tmp/", "support_ticket")):
            return True
    return False


def evaluate_budget(root: Path, command: str, *, enforce_capture_path: bool = False) -> BudgetDecision:
    if not command:
        return BudgetDecision("allow", "empty_command")
    if enforce_capture_path and _bypasses_capture_runner(command):
        return BudgetDecision(
            "deny",
            "capture_required_for_archive_or_log",
            "Run `.contextguard/bin/contextguard capture -- <command>` before stdout reaches the host.",
        )
    state = load_session_state(root)
    family = _family(command)
    family_count = sum(1 for item in state.get("commands", []) if item.get("family") == family)
    snapshot = _snapshot(root, command)
    if snapshot:
        from .optimization_advisor import _command_key

        previous = state.get("reads", {}).get(_command_key(command))
        if previous and previous.get("hashes") == snapshot:
            return BudgetDecision(
                "deny",
                "repeated_unchanged_read",
                "Reuse the prior read from this session or use `contextguard inspect` for a bounded slice.",
            )

    exact_count = sum(1 for item in state.get("commands", []) if item.get("command") == command)
    if family == "repository_listing" and exact_count >= 1:
        return BudgetDecision(
            "advise",
            "repeated_repository_listing",
            "Reuse the prior listing when it is still current; this command will run because its evidence may differ.",
        )
    if family == "full_validation" and family_count >= 2:
        return BudgetDecision(
            "advise",
            "full_validation_budget_exceeded",
            "Prefer a targeted test unless final validation is required; this command will run.",
        )
    if parts_read_like(command):
        read_count = len(state.get("reads", {}))
        source_files = _source_files_for_inspect(command, root)
        if read_count >= 2 and len(source_files) >= 2:
            return BudgetDecision(
                "deny",
                "inspect_instead_of_multi_read",
                "Use `.contextguard/bin/contextguard inspect` for the named source files in one bounded call.",
            )
    return BudgetDecision("allow", "within_budget")


def render_budget_feedback(decision: BudgetDecision) -> str:
    if decision.action == "allow":
        return ""
    label = "advice" if decision.action == "advise" else "budget enforcement"
    text = f"ContextGuard {label}: {decision.reason}."
    if decision.alternative:
        text += f" {decision.alternative}"
    return text
