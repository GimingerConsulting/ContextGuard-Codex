#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.output_compactor import compact_output
from contextguard.output_capture import NOISY_MEDIUM_BYTES, SMALL_PASSTHROUGH_BYTES
from contextguard.project import detect_project


event = read_event()
output = event.get("tool_response") or event.get("output") or event.get("result") or ""
compact = compact_output(output, "") if isinstance(output, str) else {}
raw_bytes = int(compact.get("raw_bytes", 0))
is_noisy_medium = (
    raw_bytes >= NOISY_MEDIUM_BYTES
    and (bool(compact.get("errors")) or int(compact.get("line_count", 0)) > 50)
)
if isinstance(output, str) and (raw_bytes > SMALL_PASSTHROUGH_BYTES or is_noisy_medium):
    info = detect_project()
    tmp = state_dir(info.root) / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = tmp / f"tool-output-{stamp}.txt"
    summary_path = tmp / f"tool-output-{stamp}.summary.json"
    output_path.write_text(output, encoding="utf-8", errors="replace")
    compact["full_output_path"] = output_path.as_posix()
    summary_path.write_text(json.dumps(compact, indent=2) + "\n", encoding="utf-8")
    feedback = (
        "ContextGuard compacted large tool output:\n"
        + (f"tests: {compact['test_summary']}\n" if compact.get("test_summary") else "")
        + ("failed_tests:\n" + "\n".join(f"- {name}" for name in compact["failed_tests"]) + "\n" if compact.get("failed_tests") else "")
        + "\n".join(compact["errors"] + compact["warnings"])
        + (f"\nstack_trace:\n{compact['stack_traces'][0]}" if compact.get("stack_traces") else "")
        + f"\nfull_output: {output_path}\nsummary: {summary_path}"
    )
    metrics_path = tmp / "hook-output-metrics.jsonl"
    with metrics_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"raw_bytes": raw_bytes, "model_visible_bytes": len(feedback.encode()), "compacted": True}) + "\n")
    write_event(
        {
            "decision": "block",
            "reason": feedback,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": feedback,
            },
        }
    )
else:
    write_event({})
