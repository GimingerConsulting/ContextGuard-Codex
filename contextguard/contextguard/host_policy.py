from __future__ import annotations


def render_host_enforcement_note(*, hooks_observed: bool) -> str:
    if hooks_observed:
        return (
            "ContextGuard host mode: lifecycle hooks observed. Capture rewriting and post-tool compaction "
            "can augment project-runner protection."
        )
    return (
        "ContextGuard host mode: hooks not yet observed. Protection relies on the project capture runner "
        "and AGENTS.md contract until PreToolUse/PostToolUse dispatch is trusted in Codex."
    )


def inspect_first_directive() -> str:
    return (
        "Prefer `contextguard inspect` for 1-4 named source files before repeated cat/sed reads. "
        "Use `contextguard expand <path>` only when the context brief is insufficient."
    )
