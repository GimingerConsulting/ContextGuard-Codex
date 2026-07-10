from pathlib import Path

from contextguard.doc_families import build_doc_families
from contextguard.ledger import ledger_summary, record_ledger
from contextguard.model_router import route_task
from contextguard.onboarding import initialize_project
from contextguard.session_state import MAX_COMMANDS, load_session_state, reset_session_state, save_session_state


def test_router_blocks_migration_scope(tmp_path: Path):
    result = route_task(
        tmp_path,
        "Implement the bounded fix for SUPPORT_TICKET.md.",
        likely_files=["inventory/migration.py", "inventory/service.py"],
        confidence="high",
    )
    assert result["eligible"] is False
    assert result["reason"] == "high_risk_task"
    assert "Do not spawn any subagent" in result["directive"]


def test_doc_families_group_similar_docs(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ARCHITECTURE.md").write_text("a", encoding="utf-8")
    (tmp_path / "docs" / "ARCHITECTURE_v2.md").write_text("b", encoding="utf-8")
    families = build_doc_families(tmp_path)
    assert "architecture" in families
    assert len(families["architecture"]) >= 2
    assert "path" in families["architecture"][0]
    assert "sha256" in families["architecture"][0]


def test_ledger_records_capture_events(tmp_path: Path):
    initialize_project(tmp_path)
    record_ledger(tmp_path, "capture", bytes_saved=1200, label="pytest")
    record_ledger(tmp_path, "brief", bytes_added=300, label="context_brief")
    summary = ledger_summary(tmp_path)
    assert summary["counts"]["capture"] == 1
    assert summary["counts"]["brief"] == 1
    assert summary["totals"]["bytes_saved"] >= 1200


def test_session_state_caps_recent_command_history(tmp_path: Path):
    reset_session_state(tmp_path)
    state = load_session_state(tmp_path)
    state["commands"] = [{"command": f"cmd-{index}"} for index in range(MAX_COMMANDS + 25)]

    save_session_state(tmp_path, state)
    loaded = load_session_state(tmp_path)

    assert len(loaded["commands"]) == MAX_COMMANDS
    assert loaded["commands"][0]["command"] == "cmd-25"
