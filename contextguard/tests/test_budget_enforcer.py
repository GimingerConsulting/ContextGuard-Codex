from pathlib import Path

from contextguard.budget_enforcer import evaluate_budget
from contextguard.optimization_advisor import record_command
from contextguard.session_state import record_working_set, reset_session_state


def test_repeated_read_emits_non_blocking_advice(tmp_path: Path):
    reset_session_state(tmp_path)
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    record_command(tmp_path, "cat app.py", succeeded=True)

    decision = evaluate_budget(tmp_path, "cat app.py")

    assert decision.action == "advise"
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


def test_working_set_advice_does_not_force_costly_retry_turns(tmp_path: Path):
    reset_session_state(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("def run():\n    return 1\n", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    record_working_set(tmp_path, f"- dependency app.py sha={digest} symbols=run")

    whole = evaluate_budget(tmp_path, ".contextguard/bin/contextguard inspect app.py")
    bounded = evaluate_budget(tmp_path, ".contextguard/bin/contextguard inspect app.py --symbol run")
    listing = evaluate_budget(tmp_path, "find . -maxdepth 2 -type f")

    assert whole.action == "allow"
    assert bounded.action == "allow"
    assert listing.action == "allow"


def test_working_set_does_not_block_worker_shell_discovery(tmp_path: Path):
    reset_session_state(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    import hashlib

    record_working_set(tmp_path, f"- app.py sha={hashlib.sha256(source.read_bytes()).hexdigest()[:12]}")
    decision = evaluate_budget(tmp_path, "command -v contextguard-worker || ls .contextguard/bin")

    assert decision.action == "allow"


def test_working_set_advises_after_two_followups_without_blocking(tmp_path: Path):
    reset_session_state(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    import hashlib

    record_working_set(
        tmp_path,
        f"- implementation app.py sha={hashlib.sha256(source.read_bytes()).hexdigest()[:12]} symbols=VALUE",
    )
    record_command(tmp_path, "contextguard inspect app.py --symbol VALUE", succeeded=True)
    record_command(tmp_path, "find . -maxdepth 2 -type f", succeeded=True)

    decision = evaluate_budget(tmp_path, "contextguard snapshot app.py")

    assert decision.action == "advise"
    assert decision.reason == "exploration_phase_complete"
