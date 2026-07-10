from pathlib import Path

from contextguard.model_router import route_task
from contextguard.project_context import load_project_context


def test_load_project_context_reads_support_ticket(tmp_path: Path):
    (tmp_path / "SUPPORT_TICKET.md").write_text(
        "Fix concurrent migration in inventory/migration.py\n",
        encoding="utf-8",
    )
    context = load_project_context(tmp_path)
    assert "inventory/migration.py" in context
    assert "concurrent" in context


def test_support_ticket_content_locks_worker_routing(tmp_path: Path):
    (tmp_path / "SUPPORT_TICKET.md").write_text(
        "Thread-safe migration required for payment transaction integrity.\n",
        encoding="utf-8",
    )
    supplemental = load_project_context(tmp_path, likely_files=["SUPPORT_TICKET.md"])
    result = route_task(
        tmp_path,
        "Implement the bounded fix.",
        likely_files=["inventory/service.py"],
        confidence="high",
        supplemental_text=supplemental,
    )
    assert result["eligible"] is False
    assert result["reason"] == "high_risk_task"