#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.context_capsule import build_session_capsule, persist_session_capsule
from contextguard.history_pack import archive_index_summary
from contextguard.project import detect_project
from contextguard.utils import estimate_tokens


event = read_event()
info = detect_project()
persist_session_capsule(info.root, event)
parts: list[str] = []
session_capsule = build_session_capsule(info.root, token_limit=240)
if session_capsule:
    parts.append(session_capsule)
if (state_dir(info.root) / "manifest.json").exists():
    archive = archive_index_summary(info.root)
    if int(archive.get("entries", 0)) > 0:
        parts.append(
            "ContextGuard archive index: "
            f"{archive['entries']} captures, {archive['repeated_fingerprints']} repeated fingerprints. "
            "Reuse archived evidence before re-running noisy commands."
        )
while parts and estimate_tokens("\n".join(parts)) > 320:
    parts.pop()
if parts:
    write_event(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": "\n".join(parts),
            }
        }
    )
else:
    write_event({})
