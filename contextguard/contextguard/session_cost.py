from __future__ import annotations

from pathlib import Path

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
    return {
        "session_tokens_saved_estimate": tokens_saved,
        "session_tokens_added_estimate": tokens_added,
        "session_net_tokens_saved_estimate": net_tokens_saved,
        "command_count": len(state.get("commands", [])),
        "evidence_entries": len(state.get("evidence", {})),
        "ledger_counts": ledger.get("counts", {}),
        "estimated_session_api_savings_usd": api["estimated_daily_api_savings_usd"],
        "pricing_model": api["pricing_model"],
    }