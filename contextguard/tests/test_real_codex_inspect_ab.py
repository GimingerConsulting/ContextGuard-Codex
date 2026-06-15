import json
from pathlib import Path

from benchmarks.real_codex_inspect_ab import command_evidence


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
