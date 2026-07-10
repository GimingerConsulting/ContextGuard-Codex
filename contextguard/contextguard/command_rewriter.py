from __future__ import annotations

import shlex
from pathlib import Path

from .budget_enforcer import _source_files_for_inspect
from .command_classifier import classify_command


def rewrite_for_inspect(command: str, root: Path, runner: Path | None = None) -> str | None:
    files = _source_files_for_inspect(command, root)
    if len(files) < 2 or len(files) > 4:
        return None
    executable = runner.as_posix() if runner is not None else ".contextguard/bin/contextguard"
    quoted = " ".join(shlex.quote(path) for path in files)
    return f"{shlex.quote(executable)} inspect {quoted}"


def rewrite_for_capture(command: str, runner: Path | None = None) -> str | None:
    decision = classify_command(command)
    if decision.action != "capture":
        return None
    executable = runner.as_posix() if runner is not None else "contextguard"
    return " ".join([shlex.quote(executable), "capture", "--", "sh", "-c", shlex.quote(command)])
