from pathlib import Path

from contextguard.task_classifier import classify_task
from contextguard.task_evidence import build_task_evidence
from contextguard.utils import estimate_tokens


def test_explicit_file_reference_is_ranked_first(tmp_path: Path):
    (tmp_path / "SUPPORT_TICKET.md").write_text("Customer reports inventory failure.\n", encoding="utf-8")
    (tmp_path / "other.md").write_text("Customer issue notes.\n", encoding="utf-8")

    result = classify_task(tmp_path, "Investigate the customer issue in SUPPORT_TICKET.md")

    assert result["likely_files"][0] == "SUPPORT_TICKET.md"
    assert result["top_score"] >= 1


def test_task_evidence_is_bounded_and_contains_expansion_handles(tmp_path: Path):
    (tmp_path / "SUPPORT_TICKET.md").write_text(
        "# Ticket\nCustomer reports inventory failure during retry.\n" + "noise\n" * 100,
        encoding="utf-8",
    )
    (tmp_path / "events.jsonl").write_text(
        '{"event":"failure","token":"secret-value"}\n',
        encoding="utf-8",
    )

    packet = build_task_evidence(
        tmp_path,
        "Investigate inventory failure in SUPPORT_TICKET.md and available events",
        token_limit=120,
    )

    assert "SUPPORT_TICKET.md sha=" in packet
    assert "inventory failure" in packet
    assert estimate_tokens(packet) <= 120
    assert "secret-value" not in packet


def test_task_evidence_skips_low_confidence_prompt(tmp_path: Path):
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    assert build_task_evidence(tmp_path, "please help") == ""
