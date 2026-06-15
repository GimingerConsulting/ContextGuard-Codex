#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from benchmarks.real_codex_support_ab import _run_one


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_CONTEXTGUARD_COMMAND_BASELINE = 34


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


def execute_ab(output_dir: Path, *, timeout: int = 1800) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for kind in ("raw", "contextguard"):
        with tempfile.TemporaryDirectory(prefix=f"contextguard-inspect-ab-{kind}-") as tmp:
            results[kind] = _run_one(kind, Path(tmp), output_dir / kind, timeout)
        results[kind]["command_evidence"] = command_evidence(output_dir / kind / "events.jsonl")

    raw = results["raw"]
    optimized = results["contextguard"]
    same_quality = all([
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
    accepted = all([
        same_quality,
        evidence["inspect_calls"] >= 1,
        evidence["successful_spawn_count"] == 0,
        evidence["command_executions"] < PREVIOUS_CONTEXTGUARD_COMMAND_BASELINE,
        optimized["tool_output_bytes"] <= raw["tool_output_bytes"],
    ])
    result = {
        "benchmark": "real-codex-bounded-source-inspector-ab",
        "previous_contextguard_command_baseline": PREVIOUS_CONTEXTGUARD_COMMAND_BASELINE,
        "same_quality": same_quality,
        "accepted": accepted,
        **results,
        "limitations": [
            "A single pair proves the command path and quality gate but remains subject to model stochasticity.",
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
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("choose --run")
    result = execute_ab(args.output_dir, timeout=args.timeout)
    print(json.dumps({
        "accepted": result["accepted"],
        "same_quality": result["same_quality"],
        "raw_commands": result["raw"]["command_evidence"]["command_executions"],
        "contextguard_commands": result["contextguard"]["command_evidence"]["command_executions"],
        "inspect_calls": result["contextguard"]["command_evidence"]["inspect_calls"],
    }, indent=2, sort_keys=True))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())
