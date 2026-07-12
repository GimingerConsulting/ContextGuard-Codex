#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from benchmarks.real_codex_support_ab import _run_one


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_CONTEXTGUARD_COMMAND_BASELINE = 34
MIN_UNCACHED_INPUT_REDUCTION_PERCENT = 5.0
MIN_TOOL_OUTPUT_REDUCTION_PERCENT = 10.0
MIN_CACHED_INPUT_REDUCTION_PERCENT = 0.0
MIN_OUTPUT_REDUCTION_PERCENT = 0.0


def rejection_reason(events_path: Path) -> str | None:
    text = events_path.read_text(encoding="utf-8", errors="replace").lower()
    if "usage limit" in text:
        return "codex_usage_limit"
    if "rate limit" in text:
        return "codex_rate_limit"
    return None


def reduction_percent(raw: int | float, optimized: int | float) -> float | None:
    if raw <= 0:
        return None
    return round((raw - optimized) * 100.0 / raw, 2)


def paired_efficiency(raw: dict, optimized: dict) -> dict[str, object]:
    raw_commands = raw["command_evidence"]["command_executions"]
    optimized_commands = optimized["command_evidence"]["command_executions"]
    uncached_reduction = reduction_percent(raw["uncached_input_tokens"], optimized["uncached_input_tokens"])
    cached_reduction = reduction_percent(raw["cached_input_tokens"], optimized["cached_input_tokens"])
    output_reduction = reduction_percent(raw["output_tokens"], optimized["output_tokens"])
    tool_reduction = reduction_percent(raw["tool_output_bytes"], optimized["tool_output_bytes"])
    return {
        "uncached_input_reduction_percent": uncached_reduction,
        "cached_input_reduction_percent": cached_reduction,
        "output_reduction_percent": output_reduction,
        "tool_output_reduction_percent": tool_reduction,
        "command_reduction_percent": reduction_percent(raw_commands, optimized_commands),
        "commands_below_paired_raw": optimized_commands < raw_commands,
        "meets_uncached_input_threshold": uncached_reduction is not None
        and uncached_reduction >= MIN_UNCACHED_INPUT_REDUCTION_PERCENT,
        "meets_cached_input_threshold": cached_reduction is not None
        and cached_reduction > MIN_CACHED_INPUT_REDUCTION_PERCENT,
        "meets_output_threshold": output_reduction is not None
        and output_reduction > MIN_OUTPUT_REDUCTION_PERCENT,
        "meets_tool_output_threshold": tool_reduction is not None
        and tool_reduction >= MIN_TOOL_OUTPUT_REDUCTION_PERCENT,
    }


def command_evidence(path: Path) -> dict[str, int]:
    commands = 0
    inspect_calls = 0
    spawns = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        if item.get("type") == "command_execution":
            commands += 1
            command = item.get("command") or ""
            if "contextguard inspect" in command or ".contextguard/bin/contextguard inspect" in command:
                inspect_calls += 1
        if (
            item.get("type") == "collab_tool_call"
            and item.get("tool") == "spawn_agent"
            and item.get("status") == "completed"
            and item.get("receiver_thread_ids")
        ):
            spawns += 1
    return {
        "command_executions": commands,
        "inspect_calls": inspect_calls,
        "successful_spawn_count": spawns,
    }


def execute_ab(
    output_dir: Path,
    *,
    timeout: int = 1800,
    order: tuple[str, str] = ("raw", "contextguard"),
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for kind in order:
        with tempfile.TemporaryDirectory(prefix=f"contextguard-inspect-ab-{kind}-") as tmp:
            results[kind] = _run_one(kind, Path(tmp), output_dir / kind, timeout)
        results[kind]["command_evidence"] = command_evidence(output_dir / kind / "events.jsonl")

    raw = results["raw"]
    optimized = results["contextguard"]
    rejection_reasons = {
        kind: rejection_reason(output_dir / kind / "events.jsonl") for kind in ("raw", "contextguard")
    }
    valid_run = all(
        results[kind]["codex_exit_code"] == 0 and not rejection_reasons[kind]
        for kind in ("raw", "contextguard")
    )
    same_quality = all([
        valid_run,
        raw["validation"]["exit_code"] == 0,
        optimized["validation"]["exit_code"] == 0,
        raw["validation"]["hidden_passed_tests"] == 144,
        optimized["validation"]["hidden_passed_tests"] == 144,
        {
            key: raw["validation"]["canonical_output"].get(key)
            for key in ("sku", "quantity", "remaining", "ok")
        } == {
            key: optimized["validation"]["canonical_output"].get(key)
            for key in ("sku", "quantity", "remaining", "ok")
        },
        raw["validation"]["concurrency_output"] == optimized["validation"]["concurrency_output"],
    ])
    evidence = optimized["command_evidence"]
    efficiency = paired_efficiency(raw, optimized)
    accepted = all([
        same_quality,
        evidence["inspect_calls"] >= 1,
        evidence["successful_spawn_count"] == 0,
        efficiency["commands_below_paired_raw"],
        efficiency["meets_uncached_input_threshold"],
        efficiency["meets_cached_input_threshold"],
        efficiency["meets_output_threshold"],
        efficiency["meets_tool_output_threshold"],
    ])
    result = {
        "benchmark": "real-codex-bounded-source-inspector-ab",
        "previous_contextguard_command_baseline": PREVIOUS_CONTEXTGUARD_COMMAND_BASELINE,
        "same_quality": same_quality,
        "accepted": accepted,
        "valid_run": valid_run,
        "rejection_reasons": rejection_reasons,
        "paired_efficiency": efficiency,
        **results,
        "limitations": [
            "A single pair proves the command path and quality gate but remains subject to model stochasticity.",
            f"Arm order: {' then '.join(order)}; repeated counterbalanced pairs are needed for population-level claims.",
            "Codex subscription quota accounting is not exposed by the CLI.",
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--output-dir", type=Path,
        default=PLUGIN_ROOT / "benchmarks/results/real-codex-inspect-ab-2026-06-15",
    )
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument(
        "--order",
        choices=("raw-first", "contextguard-first"),
        default="raw-first",
    )
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("choose --run")
    order = ("raw", "contextguard") if args.order == "raw-first" else ("contextguard", "raw")
    result = execute_ab(args.output_dir, timeout=args.timeout, order=order)
    print(json.dumps({
        "accepted": result["accepted"],
        "valid_run": result["valid_run"],
        "rejection_reasons": result["rejection_reasons"],
        "paired_efficiency": result["paired_efficiency"],
        "same_quality": result["same_quality"],
        "raw_commands": result["raw"]["command_evidence"]["command_executions"],
        "contextguard_commands": result["contextguard"]["command_evidence"]["command_executions"],
        "inspect_calls": result["contextguard"]["command_evidence"]["inspect_calls"],
    }, indent=2, sort_keys=True))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())
