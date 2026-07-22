from __future__ import annotations

from pathlib import Path

from .codex_usage import current_codex_usage
from .ledger import ledger_summary
from .quota_proxy import estimate_api_cost
from .session_state import load_session_state


def session_cost_report(root: Path) -> dict[str, object]:
    ledger = ledger_summary(root)
    totals = ledger.get("totals") or {}
    tokens_saved = int(totals.get("tokens_saved", 0))
    tokens_added = int(totals.get("tokens_added", 0))
    net_tokens_saved = max(0, tokens_saved - tokens_added)
    api = estimate_api_cost(net_tokens_saved)
    state = load_session_state(root)
    usage = current_codex_usage(root)
    return {
        "exact_usage_available": usage.get("available", False),
        "models_used": usage.get("models_used", []),
        "input_tokens": usage.get("input_tokens", 0),
        "cached_input_tokens": usage.get("cached_input_tokens", 0),
        "cache_write_input_tokens": usage.get("cache_write_input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "reasoning_output_tokens": usage.get("reasoning_output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "session_api_cost_usd": usage.get("api_cost_usd"),
        "api_cost_complete": usage.get("api_cost_complete", False),
        "model_breakdown": usage.get("model_breakdown", []),
        "usage_source": usage.get("source"),
        "pricing_basis": usage.get("pricing_basis"),
        "pricing_source": usage.get("pricing_source"),
        "usage_note": usage.get("note"),
        "session_tokens_saved_estimate": tokens_saved,
        "session_tokens_added_estimate": tokens_added,
        "session_net_tokens_saved_estimate": net_tokens_saved,
        "command_count": len(state.get("commands", [])),
        "evidence_entries": len(state.get("evidence", {})),
        "ledger_counts": ledger.get("counts", {}),
        "estimated_session_api_savings_usd": api["estimated_daily_api_savings_usd"],
        "pricing_model": api["pricing_model"],
    }
