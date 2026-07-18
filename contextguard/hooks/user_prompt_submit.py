#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.database import connect, increment
from contextguard.project import detect_project
from contextguard.session_state import record_working_set
from contextguard.task_classifier import classify_task
from contextguard.task_evidence import (
    build_task_evidence,
    record_task_evidence_injection,
    task_evidence_signature,
)


event = read_event()
prompt = event.get("prompt") or event.get("user_prompt") or ""
info = detect_project()
if (state_dir(info.root) / "manifest.json").exists() and prompt:
    classification = classify_task(info.root, prompt)
    parts: list[str] = []
    packet = build_task_evidence(info.root, prompt, classification=classification)
    signature = task_evidence_signature(info.root, prompt, classification=classification) if packet else ""
    if packet and signature and record_task_evidence_injection(info.root, signature, packet):
        record_working_set(info.root, packet)
        parts.append(packet)
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
