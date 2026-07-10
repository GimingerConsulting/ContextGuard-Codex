#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from _bootstrap import read_event, write_event
from contextguard.budget_enforcer import evaluate_budget, render_budget_feedback
from contextguard.command_classifier import classify_command
from contextguard.command_rewriter import rewrite_for_capture, rewrite_for_inspect
from contextguard.config import state_dir
from contextguard.hook_diagnostics import record_hook
from contextguard.optimization_advisor import analyze_command
from contextguard.project import detect_project


event = read_event()
tool = event.get("tool_name") or event.get("toolName")
tool_input = event.get("tool_input") or event.get("input") or {}
command = tool_input.get("command") or tool_input.get("cmd") or ""
if command:
    info = detect_project()
    if (state_dir(info.root) / "manifest.json").exists():
        record_hook(info.root, "PreToolUse")
        budget = evaluate_budget(info.root, command, enforce_capture_path=True)
        advice = analyze_command(info.root, command)
        budget_feedback = render_budget_feedback(budget)
        if budget_feedback and advice:
            advice = f"{budget_feedback}\n{advice}"
        elif budget_feedback:
            advice = budget_feedback
    else:
        budget = None
        advice = ""
    decision = classify_command(command)
    runner = Path(__file__).resolve().parents[1] / "scripts" / "contextguard"
    rewritten = None
    if budget is None or budget.action != "deny":
        rewritten = rewrite_for_inspect(command, info.root, runner) or rewrite_for_capture(command, runner)
    if os.environ.get("CONTEXTGUARD_BENCHMARK_METRICS") == "1":
        path = state_dir(info.root) / "tmp" / "hook-invocations.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "event": "PreToolUse",
                        "tool": tool,
                        "command": command,
                        "rewrite_requested": bool(rewritten),
                        "budget_action": getattr(budget, "action", "allow"),
                    }
                )
                + "\n"
            )
    if budget is not None and budget.action == "deny":
        write_event(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": render_budget_feedback(budget),
                    "additionalContext": render_budget_feedback(budget),
                }
            }
        )
    elif rewritten or advice:
        updated = dict(tool_input)
        if rewritten:
            if "command" in updated:
                updated["command"] = rewritten
            else:
                updated["cmd"] = rewritten
        hook_output = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
        if rewritten:
            hook_output["updatedInput"] = updated
        if advice:
            hook_output["additionalContext"] = advice
        write_event({"hookSpecificOutput": hook_output})
    else:
        write_event({})
else:
    write_event({})