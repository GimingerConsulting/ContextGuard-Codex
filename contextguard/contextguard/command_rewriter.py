from __future__ import annotations

import re
import shlex
from pathlib import Path

from .budget_enforcer import _source_files_for_inspect
from .command_classifier import _shell_script, _shell_tokens, classify_command
from .optimization_advisor import _command_key
from .session_state import load_session_state
from .utils import sha256_file


_SHELL_SEPARATORS = {";", "&&", "||", "&"}
_UNSAFE_SHELL_WORDS = {
    "if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done",
    "case", "esac", "function", "select",
}
_STRUCTURED_SUFFIXES = {".log", ".jsonl", ".json", ".csv", ".tsv", ".sql"}
_VALIDATION_COMMANDS = {
    "pytest", "ruff", "mypy", "npm", "pnpm", "yarn", "bun", "make", "cargo",
    "docker", "podman", "kubectl", "terraform", "gradle", "mvn", "gh", "tsc",
    "eslint", "vitest",
}


def _working_set_confirms_sources(root: Path, files: list[str], command: str | None = None) -> bool:
    """Allow lossy source routing only for files verified in the task packet."""
    if not files:
        return False
    if not (root / ".contextguard" / "manifest.json").is_file():
        return True
    working_set = load_session_state(root).get("working_set") or {}
    if working_set:
        for relative in files:
            entry = working_set.get(relative) or {}
            path = root / relative
            prefix = str(entry.get("sha256_prefix") or "")
            if not prefix or not path.is_file() or not sha256_file(path).startswith(prefix):
                break
        else:
            return True
    if not command:
        return False
    previous = (load_session_state(root).get("reads") or {}).get(_command_key(command)) or {}
    hashes = previous.get("hashes") or {}
    return all(
        relative in hashes
        and (root / relative).is_file()
        and sha256_file(root / relative) == hashes[relative]
        for relative in files
    )


def _source_files_for_command(command: str, root: Path) -> list[str]:
    """Find source reads inside a simple shell envelope without flattening scripts."""
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    script = _shell_script(parts)
    if script is not None:
        try:
            tokens = _shell_tokens(script)
        except ValueError:
            return []
        if not tokens or any(token in _SHELL_SEPARATORS for token in tokens):
            return []
        command = shlex.join(tokens)
    return _source_files_for_inspect(command, root)


def rewrite_for_inspect(command: str, root: Path, runner: Path | None = None) -> str | None:
    files = _source_files_for_inspect(command, root)
    if len(files) > 4:
        return None
    executable = runner.as_posix() if runner is not None else ".contextguard/bin/contextguard"
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if len(files) == 1 and (
        (parts[:1] == ["cat"] and len(parts) == 2)
        or (parts[:2] == ["nl", "-ba"] and len(parts) == 3)
    ) and _working_set_confirms_sources(root, files, command):
        return f"{shlex.quote(executable)} snapshot {shlex.quote(files[0])}"
    # A multi-file read asks for exact bodies. Rewriting it to the default
    # structural inspector would change semantics and can force retry turns.
    return None


def _contains_capture_runner(command: str) -> bool:
    return bool(re.search(r"contextguard(?:['\"]|\s)+capture\b", command, re.IGNORECASE))


def _shell_segments(command: str) -> tuple[list[str], list[tuple[list[str], str | None]]] | None:
    try:
        outer = shlex.split(command)
    except ValueError:
        return None
    script = _shell_script(outer)
    if script is None or not any(separator in script for separator in (";", "&&", "||", "&")):
        return None
    if any(marker in script for marker in ("<<", ">>", ">&", "<&")):
        return None
    try:
        tokens = _shell_tokens(script)
    except ValueError:
        return None
    if not tokens or any(token in _UNSAFE_SHELL_WORDS or token in {"|", "|&"} for token in tokens):
        return None
    entries: list[tuple[list[str], str | None]] = []
    segment: list[str] = []
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            if not segment:
                return None
            entries.append((segment, token))
            segment = []
        else:
            segment.append(token)
    if not segment:
        return None
    entries.append((segment, None))
    return outer, entries


def _segment_targets_noisy_data(parts: list[str]) -> bool:
    for value in parts[1:]:
        if value.startswith("-") or any(char in value for char in "*?[]"):
            continue
        lowered = value.lower().strip("'\"")
        if lowered in {".", "./", ".."}:
            return True
        if Path(lowered).suffix in _STRUCTURED_SUFFIXES:
            return True
        if any(marker in lowered for marker in ("/data/", "/artifacts/", "/logs/", "production.log", "failure.log")):
            return True
    return False


def _segment_is_high_yield(parts: list[str]) -> bool:
    if not parts:
        return False
    first = Path(parts[0]).name
    if first in _VALIDATION_COMMANDS:
        return True
    if first == "python3" and len(parts) >= 3 and parts[1:3] == ["-m", "pytest"]:
        return True
    if first == "go" and len(parts) > 1 and parts[1] in {"test", "build", "vet"}:
        return True
    if first == "find" or parts[:2] in (["git", "diff"], ["git", "log"]):
        return True
    if first in {"cat", "sed", "head", "tail", "awk", "jq", "rg", "grep", "curl", "wget"}:
        return _segment_targets_noisy_data(parts)
    return False


def _rewrite_compound_shell(command: str, runner: Path) -> str | None:
    parsed = _shell_segments(command)
    if parsed is None:
        return None
    outer, entries = parsed
    changed = False
    rendered: list[str] = []
    for parts, separator in entries:
        if _segment_is_high_yield(parts):
            inner = shlex.join(parts)
            captured = " ".join(
                [shlex.quote(runner.as_posix()), "capture", "--", "sh", "-c", shlex.quote(inner)]
            )
            rendered.append(captured)
            changed = True
        else:
            rendered.append(shlex.join(parts))
        if separator:
            rendered.append(separator)
    if not changed:
        return None
    return shlex.join([outer[0], outer[1], " ".join(rendered)])


def rewrite_for_capture(
    command: str,
    runner: Path | None = None,
    *,
    root: Path | None = None,
) -> str | None:
    # A model may already have followed the managed guidance. Wrapping that
    # command again creates nested capture summaries and extra follow-up
    # turns, which can cost more than the original output.
    if _contains_capture_runner(command):
        return None
    if root is not None:
        source_files = _source_files_for_command(command, root)
        if source_files and not _working_set_confirms_sources(root, source_files, command):
            # Never replace an unverified exact source read with a lossy summary.
            return None
    executable = runner or Path("contextguard")
    compound = _rewrite_compound_shell(command, executable)
    if compound is not None:
        return compound
    decision = classify_command(command)
    if decision.action != "capture":
        return None
    executable_text = executable.as_posix()
    return " ".join([shlex.quote(executable_text), "capture", "--", "sh", "-c", shlex.quote(command)])
