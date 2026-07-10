#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.cross_session import persist_cross_session_summary
from contextguard.lifetime_savings import flush_session_to_lifetime
from contextguard.evidence_expand import write_evidence_index
from contextguard.index import refresh_index
from contextguard.output_policy import inspect_final_response
from contextguard.project import detect_project


event = read_event()
if event.get("stop_hook_active"):
    write_event({})
else:
    info = detect_project()
    try:
        persist_cross_session_summary(info.root)
        flush_session_to_lifetime(info.root)
        write_evidence_index(info.root)
        refresh_index(info.root)
    except Exception:
        pass
    response = (
        event.get("response")
        or event.get("final_response")
        or event.get("agent_response")
        or event.get("message")
        or ""
    )
    if isinstance(response, str) and response.strip():
        review = inspect_final_response(response)
        if not review["valid"]:
            write_event(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "Stop",
                        "additionalContext": (
                            "ContextGuard final-response policy: compress the next reply. "
                            f"Violations: {', '.join(review['violations'])}. "
                            "Keep only changed files, validation, and real risks."
                        ),
                    }
                }
            )
        else:
            write_event({})
    else:
        write_event({})