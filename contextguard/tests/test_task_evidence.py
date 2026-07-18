from pathlib import Path

from contextguard.task_classifier import classify_task
from contextguard.session_state import load_session_state
from contextguard.task_evidence import (
    build_task_evidence,
    record_task_evidence_injection,
    task_evidence_signature,
)
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


def test_task_evidence_signature_tracks_material_changes(tmp_path: Path):
    ticket = tmp_path / "SUPPORT_TICKET.md"
    ticket.write_text("Customer reports inventory failure.\n", encoding="utf-8")

    prompt = "Investigate inventory failure in SUPPORT_TICKET.md"
    first = task_evidence_signature(tmp_path, prompt)
    second = task_evidence_signature(tmp_path, prompt)
    ticket.write_text("Customer reports inventory failure after retry.\n", encoding="utf-8")
    third = task_evidence_signature(tmp_path, prompt)

    assert first
    assert first == second
    assert first != third


def test_task_evidence_injection_records_once_per_signature(tmp_path: Path):
    ticket = tmp_path / "SUPPORT_TICKET.md"
    ticket.write_text("Customer reports inventory failure.\n", encoding="utf-8")

    prompt = "Investigate inventory failure in SUPPORT_TICKET.md"
    packet = build_task_evidence(tmp_path, prompt)
    signature = task_evidence_signature(tmp_path, prompt)

    assert packet
    assert signature
    assert record_task_evidence_injection(tmp_path, signature, packet) is True
    assert record_task_evidence_injection(tmp_path, signature, packet) is False

    state = load_session_state(tmp_path)
    assert signature in state["task_evidence"]
    assert state["task_evidence"][signature]["occurrences"] == 2


def test_task_evidence_follows_test_imports_into_implementation_symbols(tmp_path: Path):
    (tmp_path / "SUPPORT_TICKET.md").write_text(
        "Retries reserve stock twice and parallel checkout oversells inventory. Production logs attached.\n",
        encoding="utf-8",
    )
    package = tmp_path / "inventory"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text(
        "class InventoryService:\n"
        "    def reserve(self, sku, quantity, request_id):\n"
        "        self.available -= quantity\n"
        "        return {'ok': True}\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_inventory.py").write_text(
        "from inventory.service import InventoryService\n\n"
        "def test_retry():\n"
        "    service = InventoryService()\n"
        "    assert service.reserve('widget', 1, 'same')['ok']\n",
        encoding="utf-8",
    )
    data = tmp_path / "production.log"
    data.write_text("ERROR checkout oversold stock request=secret-1\n" * 20, encoding="utf-8")

    packet = build_task_evidence(
        tmp_path,
        "Investigate SUPPORT_TICKET.md and fix the inventory retry tests",
        token_limit=500,
    )

    assert "implementation inventory/service.py" in packet
    assert "def reserve" in packet
    assert "evidence production.log" in packet
    assert "secret-1" not in packet
    assert "do not reread unchanged listed files" in packet
    assert estimate_tokens(packet) <= 500
