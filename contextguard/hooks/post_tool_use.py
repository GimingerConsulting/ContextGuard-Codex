#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone

from _bootstrap import read_event, write_event
from contextguard.config import state_dir
from contextguard.hook_diagnostics import record_hook
from contextguard.evidence_expand import build_evidence_expand_directive
from contextguard.optimization_advisor import record_command
from contextguard.adaptive_capture import should_compact as adaptive_should_compact
from contextguard.history_pack import record_archive_metadata
from contextguard.output_compactor import compact_output, finalize_evidence
from contextguard.output_capture import NOISY_MEDIUM_BYTES, SMALL_PASSTHROUGH_BYTES
from contextguard.project import detect_project
from contextguard.session_state import record_evidence


event = read_event()
info = detect_project()
tool_input = event.get("tool_input") or event.get("input") or {}
command = tool_input.get("command") or tool_input.get("cmd") or ""
response = event.get("tool_response") or event.get("output") or event.get("result") or ""
response_exit = response.get("exit_code") if isinstance(response, dict) else None
exit_code = event.get("exit_code", response_exit)
if (state_dir(info.root) / "manifest.json").exists():
    record_hook(info.root, "PostToolUse")
    record_command(info.root, command, succeeded=exit_code in (None, 0))
output = event.get("tool_response") or event.get("output") or event.get("result") or ""
compact = compact_output(output, "") if isinstance(output, str) else {}
raw_bytes = int(compact.get("raw_bytes", 0))
is_noisy_medium = (
    raw_bytes >= NOISY_MEDIUM_BYTES
    and (bool(compact.get("errors")) or int(compact.get("line_count", 0)) > 50)
)
should_compact = (
    raw_bytes > SMALL_PASSTHROUGH_BYTES
    or is_noisy_medium
    or adaptive_should_compact(
        raw_bytes,
        info.root,
        has_errors=bool(compact.get("errors")),
        line_count=int(compact.get("line_count", 0)),
    )
)
if isinstance(output, str) and should_compact:
    tmp = state_dir(info.root) / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = tmp / f"tool-output-{stamp}.txt"
    summary_path = tmp / f"tool-output-{stamp}.summary.json"
    output_path.write_text(output, encoding="utf-8", errors="replace")
    display_output_path = output_path.relative_to(info.root).as_posix()
    compact["exit_code"] = exit_code
    finalize_evidence(compact)
    compact["full_output_path"] = output_path.as_posix()
    evidence_block = compact.get("evidence") or {}
    compact["repeated_evidence"] = record_evidence(
        info.root,
        compact["evidence_fingerprint"],
        summary_path.as_posix(),
        locations=list(evidence_block.get("locations") or []),
        failed_tests=list(evidence_block.get("failed_tests") or []),
    )
    compact["expand_directive"] = build_evidence_expand_directive(info.root, compact["evidence_fingerprint"])
    summary_path.write_text(json.dumps(compact, indent=2) + "\n", encoding="utf-8")
    record_archive_metadata(
        info.root,
        archive_path=summary_path.as_posix(),
        fingerprint=compact["evidence_fingerprint"],
        raw_bytes=raw_bytes,
    )
    repeated = compact["repeated_evidence"]
    if repeated["repeated"]:
        feedback = (
            f"ContextGuard repeated evidence ({repeated['occurrences']}); reuse prior diagnosis.\n"
        )
        if compact.get("test_summary"):
            feedback += f"tests: {compact['test_summary']}\n"
        if compact.get("failed_tests"):
            feedback += "failed_tests:\n" + "\n".join(
                f"- {name}" for name in compact["failed_tests"][:3]
            ) + "\n"
        feedback += f"full_output: {display_output_path}"
    else:
        locations = (compact.get("evidence") or {}).get("locations") or []
        escalation = compact.get("escalation") or {}
        feedback = (
            "ContextGuard compacted large tool output:\n"
            + (f"tests: {compact['test_summary']}\n" if compact.get("test_summary") else "")
            + ("failed_tests:\n" + "\n".join(f"- {name}" for name in compact["failed_tests"]) + "\n" if compact.get("failed_tests") else "")
            + ("locations:\n" + "\n".join(f"- {name}" for name in locations) + "\n" if locations else "")
            + "\n".join(compact["errors"] + compact["warnings"])
            + (f"\nstack_trace:\n{compact['stack_traces'][0]}" if compact.get("stack_traces") else "")
            + (f"\nescalation: {escalation['reason']}" if escalation.get("required") else "")
            + (f"\n{compact['expand_directive']}" if compact.get("expand_directive") else "")
            + f"\nfull_output: {display_output_path}"
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
