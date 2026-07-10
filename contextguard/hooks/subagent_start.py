#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.hook_diagnostics import record_hook
from contextguard.project import detect_project
from contextguard.risk_assessment import render_no_delegation_directive
from contextguard.session_state import load_session_state, record_routing_event


event = read_event()
info = detect_project()
agent_type = event.get("agent_type") or event.get("agentType") or event.get("type") or ""
model = event.get("model") or ""
thread_id = event.get("thread_id") or event.get("threadId") or ""
if (state_dir(info.root) / "manifest.json").exists():
    record_hook(info.root, "SubagentStart")
    record_routing_event(
        info.root,
        {"event": "start", "agent_type": agent_type, "model": model, "thread_id": thread_id},
    )
session = load_session_state(info.root) if (state_dir(info.root) / "manifest.json").exists() else {}
routing_locked = bool(session.get("routing_locked"))
if agent_type == "contextguard-worker":
    if routing_locked:
        directive = render_no_delegation_directive(
            {"locked": True, "reasons": session.get("routing_lock_reasons", [])}
        )
        write_event(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "ContextGuard routing lock: high-risk task blocks worker delegation."
                    ),
                    "additionalContext": directive or (
                        "ContextGuard routing lock: do not spawn contextguard-worker. "
                        "Continue on the parent model."
                    ),
                }
            }
        )
    else:
        write_event(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": (
                        "Execute only the bounded package from the parent. Do not broaden scope or spawn agents. "
                        "Edit assigned files, run focused tests, and report ambiguity instead of guessing."
                    ),
                }
            }
        )
else:
    write_event({})
