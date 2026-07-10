#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.hook_diagnostics import record_hook
from contextguard.onboarding import initialize_project
from contextguard.project import detect_project
from contextguard.cross_session import persist_cross_session_summary, render_cross_session_brief
from contextguard.lifetime_savings import flush_session_to_lifetime
from contextguard.session_gate import build_session_gate
from contextguard.session_state import reset_session_state


event = read_event()
info = detect_project()
if (state_dir(info.root) / "manifest.json").exists():
    record_hook(info.root, "SessionStart")
    persist_cross_session_summary(info.root)
    flush_session_to_lifetime(info.root)
    reset_session_state(info.root)
    gate = build_session_gate(info.root)
    prior = render_cross_session_brief(info.root)
    context = "\n".join(part for part in (prior, gate) if part)
    write_event(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }
    )
else:
    try:
        result = initialize_project(info.root)
        record_hook(result.project.root, "SessionStart")
        reset_session_state(result.project.root)
        message = "ContextGuard initialized automatically for this project. Continue with the user's task normally."
    except Exception as exc:
        message = f"ContextGuard automatic setup failed: {exc}. Run `$contextguard-setup` to diagnose and retry."
    write_event({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": message}})
