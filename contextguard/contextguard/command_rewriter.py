from __future__ import annotations

import shlex
from pathlib import Path

from .budget_enforcer import _source_files_for_inspect
from .command_classifier import classify_command


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
    ):
        return f"{shlex.quote(executable)} snapshot {shlex.quote(files[0])}"
    # A multi-file read asks for exact bodies. Rewriting it to the default
    # structural inspector would change semantics and can force retry turns.
    return None


def rewrite_for_capture(command: str, runner: Path | None = None) -> str | None:
    decision = classify_command(command)
    if decision.action != "capture":
        return None
    executable = runner.as_posix() if runner is not None else "contextguard"
    return " ".join([shlex.quote(executable), "capture", "--", "sh", "-c", shlex.quote(command)])
