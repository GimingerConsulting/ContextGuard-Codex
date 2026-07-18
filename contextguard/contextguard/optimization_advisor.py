from __future__ import annotations

import hashlib
import shlex
from pathlib import Path

from .session_state import load_session_state, save_session_state
from .utils import sha256_file


COMMAND_MILESTONE = 10
INSPECT_ADVICE_AFTER_READS = 2
EVIDENCE_ESCALATION_DIRECTIVE = (
    "ContextGuard evidence escalation: compacted output already contains failures, locations, "
    "and archived evidence. Do not re-read the same log, test output, or multi-file inspection. "
    "Inspect or patch only the missing named file or symbol next."
)


def _command_key(command: str) -> str:
    return hashlib.sha256(command.strip().encode()).hexdigest()


def _safe_path(root: Path, value: str) -> Path | None:
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def _read_paths(root: Path, command: str) -> list[Path]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    if not parts or any(token in command for token in ("|", ";", "&&", "||", ">", "<")):
        return []
    if parts[0] == "cat" and len(parts) >= 2 and not any(part.startswith("-") for part in parts[1:]):
        values = parts[1:]
    elif parts[:2] == ["nl", "-ba"] and len(parts) >= 3:
        values = parts[2:]
    elif parts[0] == "sed" and len(parts) >= 4 and parts[1] == "-n":
        values = parts[3:]
    else:
        return []
    paths = [_safe_path(root, value) for value in values]
    return [path for path in paths if path is not None] if all(paths) else []


def _snapshot(root: Path, command: str) -> dict[str, str]:
    return {
        path.relative_to(root.resolve()).as_posix(): sha256_file(path)
        for path in _read_paths(root, command)
    }


def parts_read_like(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    if parts[0] == "cat" and len(parts) >= 2:
        return True
    if parts[:2] == ["nl", "-ba"] and len(parts) >= 3:
        return True
    return parts[0] == "sed" and len(parts) >= 4 and parts[1] == "-n"


def _family(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        return "other"
    if not parts:
        return "other"
    joined = " ".join(parts)
    if parts[:2] == ["rg", "--files"] or parts[0] == "find" or (
        parts[0] == "ls" and any("R" in part for part in parts[1:] if part.startswith("-"))
    ):
        return "repository_listing"
    is_pytest = parts[0] == "pytest" or (
        len(parts) >= 3
        and parts[0].rsplit("/", 1)[-1] in {"python", "python3"}
        and parts[1:3] == ["-m", "pytest"]
    )
    if is_pytest:
        targeted = any("::" in part or part.endswith(".py") for part in parts)
        return "targeted_validation" if targeted else "full_validation"
    if joined.startswith("git diff") or joined.startswith("git status"):
        return "repository_check"
    if parts[0] in {"rg", "grep"} and parts[:2] != ["rg", "--files"]:
        return "search"
    return "other"


def _emit_once(root: Path, state: dict, key: str, message: str, metric: str) -> str:
    emitted = state.setdefault("advice_emitted", [])
    if key in emitted:
        return ""
    emitted.append(key)
    metrics = state.setdefault("metrics", {})
    metrics[metric] = int(metrics.get(metric, 0)) + 1
    save_session_state(root, state)
    return message


def _evidence_reuse_advice(root: Path, state: dict, command: str) -> str:
    family = _family(command)
    if family not in {"repository_check", "full_validation", "targeted_validation", "search"}:
        return ""
    if not state.get("evidence"):
        return ""
    return _emit_once(
        root,
        state,
        f"evidence:{family}",
        EVIDENCE_ESCALATION_DIRECTIVE,
        "budget_advice_emitted",
    )


def analyze_command(root: Path, command: str) -> str:
    state = load_session_state(root)
    snapshot = _snapshot(root, command)
    previous = state.get("reads", {}).get(_command_key(command))
    if snapshot and previous and previous.get("hashes") == snapshot:
        return _emit_once(
            root,
            state,
            f"read:{_command_key(command)}",
            "ContextGuard: this exact read is unchanged in the current session. "
            "Reuse the prior content unless a fresh read is required.",
            "repeated_reads_detected",
        )

    family = _family(command)
    family_count = sum(1 for item in state.get("commands", []) if item.get("family") == family)
    read_count = len(state.get("reads", {}))
    if read_count >= INSPECT_ADVICE_AFTER_READS and parts_read_like(command):
        return _emit_once(
            root,
            state,
            "budget:inspect_instead_of_reads",
            "ContextGuard command budget: multiple direct reads already ran. "
            "Use `contextguard inspect` for 1-4 named source files instead of more cat/sed reads.",
            "budget_advice_emitted",
        )
    if family == "repository_listing" and family_count >= 1:
        return _emit_once(
            root,
            state,
            "budget:repository_listing",
            "ContextGuard command budget: a repository listing already ran. "
            "Reuse it or group the next inspection into one scoped command.",
            "budget_advice_emitted",
        )
    if family == "full_validation" and family_count >= 2:
        advice = _emit_once(
            root,
            state,
            "budget:full_validation",
            "ContextGuard command budget: two full validations already ran. "
            "Prefer targeted tests until the required final full validation.",
            "budget_advice_emitted",
        )
        if advice:
            return advice
    if family == "repository_check" and family_count >= 2:
        return _emit_once(
            root,
            state,
            "budget:repository_check",
            "ContextGuard command budget: repository checks already ran twice. "
            "Group the next diff, status, and validation inspection.",
            "budget_advice_emitted",
        )
    if family == "search" and family_count >= 3:
        return _emit_once(
            root,
            state,
            "budget:search",
            "ContextGuard: three searches already ran. Reuse their hits; inspect or patch one named file next.",
            "budget_advice_emitted",
        )
    command_count = len(state.get("commands", []))
    if command_count >= COMMAND_MILESTONE:
        return _emit_once(
            root,
            state,
            f"budget:milestone:{COMMAND_MILESTONE}",
            f"ContextGuard command budget: {COMMAND_MILESTONE} commands have run. "
            "Group remaining inspection and checkpoint verified facts before continuing.",
            "budget_advice_emitted",
        )
    return ""


def analyze_completed_command(root: Path, command: str) -> str:
    state = load_session_state(root)
    family = _family(command)
    family_count = sum(1 for item in state.get("commands", []) if item.get("family") == family)
    if family == "full_validation" and family_count >= 2:
        advice = _emit_once(
            root,
            state,
            "budget:full_validation",
            "ContextGuard command budget: two full validations have now run. "
            "Prefer targeted tests until another final full validation is genuinely required.",
            "budget_advice_emitted",
        )
        if advice:
            return advice
    return _evidence_reuse_advice(root, state, command)


def record_command(root: Path, command: str, *, succeeded: bool) -> None:
    if not command:
        return
    state = load_session_state(root)
    state.setdefault("commands", []).append({"command": command, "family": _family(command)})
    snapshot = _snapshot(root, command) if succeeded else {}
    if snapshot:
        state.setdefault("reads", {})[_command_key(command)] = {"hashes": snapshot}
    save_session_state(root, state)
