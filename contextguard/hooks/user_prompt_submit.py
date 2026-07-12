#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.database import connect, increment
from contextguard.model_router import route_task
from contextguard.project import detect_project
from contextguard.project_context import load_project_context
from contextguard.risk_assessment import render_no_delegation_directive
from contextguard.session_state import load_session_state
from contextguard.task_classifier import classify_task
from contextguard.task_evidence import build_task_evidence


event = read_event()
prompt = event.get("prompt") or event.get("user_prompt") or ""
info = detect_project()
if (state_dir(info.root) / "manifest.json").exists() and prompt:
    classification = classify_task(info.root, prompt)
    supplemental = load_project_context(info.root, likely_files=classification["likely_files"])
    routing = route_task(
        info.root,
        prompt,
        likely_files=classification["likely_files"],
        confidence=classification["confidence"],
        supplemental_text=supplemental,
    )
    session = load_session_state(info.root)
    # SessionStart already injects cross-session and checkpoint context. Repeating it here
    # makes every new user turn larger without adding new evidence.
    parts = [
        part
        for part in (
            build_task_evidence(info.root, prompt, token_limit=320, classification=classification),
        )
        if part
    ]
    if session.get("routing_locked"):
        parts.append(render_no_delegation_directive({"locked": True, "reasons": session.get("routing_lock_reasons", [])}))
    elif routing["eligible"]:
        parts.append(str(routing["directive"]))
    elif routing.get("directive"):
        parts.append(str(routing["directive"]))
    context = "\n".join(parts)
    conn = connect(state_dir(info.root) / "index.sqlite")
    increment(conn, "context_bytes_added", len(context.encode()))
    if context:
        write_event(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    else:
        write_event({})
else:
    write_event({})
