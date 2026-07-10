from contextguard.ledger import record_ledger
from contextguard.onboarding import initialize_project
from contextguard.session_cost import session_cost_report


def test_session_cost_reports_net_savings(tmp_path):
    initialize_project(tmp_path)
    record_ledger(tmp_path, "capture", bytes_saved=4000, label="pytest")
    record_ledger(tmp_path, "brief", bytes_added=500, label="gate")

    report = session_cost_report(tmp_path)

    assert report["session_tokens_saved_estimate"] > 0
    assert report["session_net_tokens_saved_estimate"] > 0
    assert "estimated_session_api_savings_usd" in report