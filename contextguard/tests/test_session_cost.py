from contextguard.ledger import record_ledger
from contextguard.onboarding import initialize_project
from contextguard.cli import _print_metric_block
from contextguard.session_cost import session_cost_report


def test_session_cost_reports_net_savings(tmp_path, monkeypatch):
    initialize_project(tmp_path)
    record_ledger(tmp_path, "capture", bytes_saved=4000, label="pytest")
    record_ledger(tmp_path, "brief", bytes_added=500, label="gate")

    monkeypatch.setattr(
        "contextguard.session_cost.current_codex_usage",
        lambda root: {
            "available": True,
            "models_used": ["gpt-5.6-sol"],
            "input_tokens": 1000,
            "cached_input_tokens": 800,
            "cache_write_input_tokens": 0,
            "output_tokens": 100,
            "reasoning_output_tokens": 20,
            "total_tokens": 1100,
            "api_cost_usd": 0.0034,
            "model_breakdown": [],
            "source": "/tmp/session.jsonl",
            "pricing_basis": "standard",
            "note": "test",
        },
    )
    report = session_cost_report(tmp_path)

    assert report["session_tokens_saved_estimate"] > 0
    assert report["session_net_tokens_saved_estimate"] > 0
    assert "estimated_session_api_savings_usd" in report
    assert report["models_used"] == ["gpt-5.6-sol"]
    assert report["total_tokens"] == 1100
    assert report["session_api_cost_usd"] == 0.0034


def test_metric_output_distinguishes_exact_tokens_from_estimates(capsys):
    _print_metric_block(
        "usage",
        {"input_tokens": 100, "session_tokens_saved_estimate": 20},
    )

    output = capsys.readouterr().out
    assert "input_tokens: 100\n" in output
    assert "input_tokens: 100 (estimate)" not in output
    assert "session_tokens_saved_estimate: 20 (estimate)" in output
