from pathlib import Path

from contextguard.budget_enforcer import evaluate_budget
from contextguard.optimization_advisor import record_command
from contextguard.session_state import reset_session_state


def test_repeated_read_is_denied(tmp_path: Path):
    reset_session_state(tmp_path)
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    record_command(tmp_path, "cat app.py", succeeded=True)

    decision = evaluate_budget(tmp_path, "cat app.py")

    assert decision.action == "deny"
    assert decision.reason == "repeated_unchanged_read"


def test_third_full_validation_emits_non_blocking_advice(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "pytest -q", succeeded=True)
    record_command(tmp_path, "pytest -q", succeeded=True)

    decision = evaluate_budget(tmp_path, "pytest -q")

    assert decision.action == "advise"
    assert decision.reason == "full_validation_budget_exceeded"


def test_direct_log_tail_without_capture_is_denied(tmp_path: Path):
    decision = evaluate_budget(tmp_path, "tail -n 50 service.log", enforce_capture_path=True)
    assert decision.action == "deny"
    assert decision.reason == "capture_required_for_archive_or_log"


def test_second_repository_listing_emits_non_blocking_advice(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "find . -name '*.py'", succeeded=True)

    decision = evaluate_budget(tmp_path, "find . -name '*.py'")

    assert decision.action == "advise"
    assert decision.reason == "repeated_repository_listing"
