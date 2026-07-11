import json
from pathlib import Path

from benchmarks.real_codex_inspect_ab import command_evidence, paired_efficiency, rejection_reason


def test_command_evidence_counts_completed_commands_and_inspect_usage(tmp_path: Path):
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": "contextguard inspect a.py b.py"}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "python3 -m pytest -q"}},
        {"type": "item.started", "item": {"type": "command_execution", "command": "ignored"}},
        {"type": "item.completed", "item": {"type": "collab_tool_call", "tool": "spawn_agent", "status": "completed", "receiver_thread_ids": ["worker"]}},
    ]
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

    evidence = command_evidence(path)

    assert evidence == {"command_executions": 2, "inspect_calls": 1, "successful_spawn_count": 1}


def test_rejection_reason_marks_usage_limited_run_invalid(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"type":"error","message":"You have hit your usage limit"}\n', encoding="utf-8")

    assert rejection_reason(path) == "codex_usage_limit"


def test_paired_efficiency_requires_material_savings_against_raw():
    raw = {
        "uncached_input_tokens": 10_000,
        "tool_output_bytes": 20_000,
        "command_evidence": {"command_executions": 20},
    }
    optimized = {
        "uncached_input_tokens": 7_500,
        "tool_output_bytes": 12_000,
        "command_evidence": {"command_executions": 12},
    }

    result = paired_efficiency(raw, optimized)

    assert result["uncached_input_reduction_percent"] == 25.0
    assert result["tool_output_reduction_percent"] == 40.0
    assert result["command_reduction_percent"] == 40.0
    assert result["commands_below_paired_raw"] is True
    assert result["meets_uncached_input_threshold"] is True
    assert result["meets_tool_output_threshold"] is True


def test_paired_efficiency_rejects_token_regression_even_with_fewer_commands():
    raw = {
        "uncached_input_tokens": 10_000,
        "tool_output_bytes": 20_000,
        "command_evidence": {"command_executions": 20},
    }
    optimized = {
        "uncached_input_tokens": 11_000,
        "tool_output_bytes": 19_000,
        "command_evidence": {"command_executions": 10},
    }

    result = paired_efficiency(raw, optimized)

    assert result["meets_uncached_input_threshold"] is False
    assert result["meets_tool_output_threshold"] is False
