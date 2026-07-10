from contextguard.onboarding import initialize_project
from contextguard.quota_proxy import estimate_api_cost, quota_proxy_report


def test_estimate_api_cost_returns_positive_savings_for_tokens():
    data = estimate_api_cost(10_000)
    assert data["estimated_daily_api_savings_usd"] > 0
    assert data["pricing_model"] == "GPT-5.5 proxy"


def test_quota_proxy_report_includes_subscription_note(tmp_path):
    initialize_project(tmp_path)
    report = quota_proxy_report(tmp_path)
    assert report["subscription_quota_multiplier_verified"] is False
    assert "Codex subscription" in report["note"]