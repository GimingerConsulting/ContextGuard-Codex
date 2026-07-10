#!/usr/bin/env python3
from __future__ import annotations

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.context_capsule import persist_session_capsule
from contextguard.cross_session import load_cross_session_summary
from contextguard.history_pack import archive_index_summary
from contextguard.project import detect_project


event = read_event()
info = detect_project()
persist_session_capsule(info.root, event)
parts: list[str] = []
if (state_dir(info.root) / "manifest.json").exists():
    archive = archive_index_summary(info.root)
    if int(archive.get("entries", 0)) > 0:
        parts.append(
            "ContextGuard archive index: "
            f"{archive['entries']} captures, {archive['repeated_fingerprints']} repeated fingerprints. "
            "Reuse archived evidence before re-running noisy commands."
        )
    prior = load_cross_session_summary(info.root)
    checkpoint = prior.get("checkpoint") or {}
    objective = checkpoint.get("current_objective")
    if objective:
        parts.append(f"ContextGuard prior objective: {objective}")
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
