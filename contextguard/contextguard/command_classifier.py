from __future__ import annotations

import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandDecision:
    action: str
    reason: str


_SHELL_NAMES = {"sh", "bash", "zsh", "dash", "ksh"}
_SHELL_CONTROL_TOKENS = {";", "&&", "||", "|", "|&", "&", "then", "do", "else", "{"}


def _shell_script(parts: list[str]) -> str | None:
    if len(parts) < 3 or parts[0].rsplit("/", 1)[-1] not in _SHELL_NAMES:
        return None
    if parts[1] not in {"-c", "-lc", "--command"}:
        return None
    return parts[2]


def _shell_tokens(script: str) -> list[str]:
    lexer = shlex.shlex(script, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    return list(lexer)


def _simple_shell_command(parts: list[str]) -> list[str] | None:
    """Return one inner command, but never flatten a shell script.

    Rewriting a compound shell script to one capture call can hide exact
    source reads behind a summary and make the model issue costly follow-up
    reads. Automatic routing is therefore limited to a single command with
    no shell control operators. Compound scripts remain untouched; the model
    can still opt into the project runner for them when it has enough context.
    """
    script = _shell_script(parts)
    if script is None:
        return None
    try:
        tokens = _shell_tokens(script)
    except ValueError:
        return None
    if not tokens or any(token in _SHELL_CONTROL_TOKENS for token in tokens):
        return None
    return tokens


def _classify_parts(parts: list[str]) -> CommandDecision:
    joined = " ".join(parts)
    destructive = {"rm", "mv", "git reset", "git checkout", "git clean"}
    if any(joined.startswith(item) for item in destructive):
        return CommandDecision("allow", "Destructive or state-changing command is not rewritten.")
    first = parts[0]
    file_like_parts = [
        part for part in parts[1:]
        if not part.startswith("-")
        and part not in {"|", ">", ">>", "2>&1"}
        and ("/" in part or "." in part)
    ]
    python_module = None
    if first.rsplit("/", 1)[-1] in {"python", "python3"} and len(parts) >= 3 and parts[1] == "-m":
        python_module = parts[2]
    if first == "cat" and len(parts) >= 2:
        return CommandDecision("capture", "Raw cat output can be large.")
    if first == "find":
        return CommandDecision("capture", "Recursive find output can be large.")
    if first == "ls" and any(flag in parts for flag in ("-R", "-laR", "-alR")):
        return CommandDecision("capture", "Recursive ls output can be large.")
    if parts[:2] == ["git", "diff"] and "--stat" not in parts:
        return CommandDecision("capture", "git diff can emit large patches.")
    if parts[:2] == ["git", "log"] and not any(p.startswith("--oneline") for p in parts):
        return CommandDecision("capture", "Verbose git log can be compacted.")
    validation_commands = {
        "pytest", "ruff", "mypy", "npm", "pnpm", "yarn", "bun", "make",
        "cargo", "docker", "podman", "kubectl", "terraform", "gradle", "mvn",
        "gh", "tsc", "eslint", "vitest",
    }
    go_validation = first == "go" and len(parts) > 1 and parts[1] in {"test", "build", "vet"}
    if first in validation_commands or go_validation or python_module in {"pytest", "ruff", "mypy"}:
        return CommandDecision("capture", "Validation command output is captured to preserve complete logs.")
    if first in {"curl", "wget"} and any(
        part in joined for part in ("api", ".json", ".jsonl", "application/json")
    ):
        return CommandDecision("capture", "Structured network output can be summarized compactly.")
    if first in {"grep", "rg"} and any(flag in parts for flag in ("-r", "-R", "--recursive")):
        return CommandDecision("capture", "Recursive search output can be large.")
    if first in {"tar", "unzip", "zipinfo"}:
        return CommandDecision("capture", "Archive listings can be large.")
    if first in {"sed", "head", "tail", "awk", "jq", "rg", "grep"} and len(file_like_parts) >= 3:
        return CommandDecision("capture", "Inspection spans multiple files and can emit large output.")
    if any(part.endswith((".json", ".jsonl", ".csv", ".tsv", ".log", ".sql")) for part in parts[1:]):
        return CommandDecision("capture", "Structured or log output can be summarized compactly.")
    if any(part in joined for part in ("node_modules", "dist/", "build/", "coverage/")):
        return CommandDecision("guide", "Command targets generated or dependency output.")
    return CommandDecision("allow", "Command appears small or already scoped.")


def classify_command(command: str, *, _allow_shell_unwrap: bool = True) -> CommandDecision:
    try:
        parts = shlex.split(command)
    except ValueError:
        return CommandDecision("allow", "Unable to parse shell safely; leaving command unchanged.")
    if not parts:
        return CommandDecision("allow", "Empty command.")

    if _allow_shell_unwrap:
        shell_script = _shell_script(parts)
        script_parts = _simple_shell_command(parts)
        if script_parts:
            decision = classify_command(
                shlex.join(script_parts),
                _allow_shell_unwrap=False,
            )
            if decision.action == "capture":
                return CommandDecision(
                    "capture",
                    f"Simple shell envelope contains capturable output: {decision.reason}",
                )
            if decision.action == "guide":
                return decision
            return CommandDecision("allow", "Shell envelope appears small or already scoped.")
        if shell_script is not None:
            return CommandDecision(
                "allow",
                "Compound shell envelope is left unchanged to preserve exact command output.",
            )

    return _classify_parts(parts)
