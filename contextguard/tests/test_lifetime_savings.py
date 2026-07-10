from contextguard.ledger import record_ledger
from contextguard.lifetime_savings import flush_session_to_lifetime, lifetime_savings_report
from contextguard.onboarding import initialize_project
from contextguard.session_state import load_session_state, save_session_state


def test_flush_session_accumulates_lifetime_totals(tmp_path):
    initialize_project(tmp_path)
    state = load_session_state(tmp_path)
    state["ledger_totals"] = {"tokens_saved": 1200, "tokens_added": 200}
    state["ledger"] = {"capture": 2, "brief": 1}
    state["commands"] = [{"command": "pytest"}]
    save_session_state(tmp_path, state)

    first = flush_session_to_lifetime(tmp_path)
    second = flush_session_to_lifetime(tmp_path)

    assert first["flushed"] is True
    assert first["lifetime_sessions"] == 1
    assert first["lifetime_net_tokens_saved"] == 1000
    assert second["flushed"] is False
    assert second["reason"] == "already_flushed"


def test_lifetime_savings_report_includes_aggregate_fields(tmp_path):
    initialize_project(tmp_path)
    record_ledger(tmp_path, "capture", bytes_saved=8000, label="pytest")
    state = load_session_state(tmp_path)
    state["ledger_totals"] = {"tokens_saved": 2000, "tokens_added": 0}
    state["ledger"] = {"capture": 1}
    state["commands"] = [{"command": "pytest"}]
    save_session_state(tmp_path, state)
    flush_session_to_lifetime(tmp_path)

    report = lifetime_savings_report(tmp_path)

    assert report["lifetime_sessions"] == 1
    assert report["lifetime_net_tokens_saved_estimate"] == 2000
    assert report["lifetime_combined_net_tokens_saved_estimate"] >= 2000
    assert "estimated_lifetime_api_savings_usd" in report
    assert "Codex sessions" in report["note"]