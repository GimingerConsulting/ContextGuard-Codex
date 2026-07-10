from __future__ import annotations

from pathlib import Path

from .config import database_path
from .database import connect


DEFAULT_MIX = {
    "cached_input_share": 0.88,
    "uncached_input_share": 0.08,
    "output_share": 0.04,
}

GPT55_RATES = {
    "uncached_input_per_m": 5.0,
    "cached_input_per_m": 0.5,
    "output_per_m": 30.0,
}


def estimate_api_cost(tokens_saved: int, *, savings_share: float = 0.41) -> dict[str, float]:
    gross_tokens = tokens_saved / savings_share if savings_share else 0.0
    saved_cost = (
        gross_tokens
        * DEFAULT_MIX["uncached_input_share"]
        * GPT55_RATES["uncached_input_per_m"]
        / 1_000_000
    )
    saved_cost += (
        gross_tokens
        * DEFAULT_MIX["cached_input_share"]
        * GPT55_RATES["cached_input_per_m"]
        / 1_000_000
    )
    saved_cost += (
        gross_tokens
        * DEFAULT_MIX["output_share"]
        * GPT55_RATES["output_per_m"]
        / 1_000_000
    ) * 0.2
    return {
        "estimated_gross_tokens": round(gross_tokens),
        "estimated_monthly_api_savings_usd": round(saved_cost * 30, 2),
        "estimated_daily_api_savings_usd": round(saved_cost, 4),
        "pricing_model": "GPT-5.5 proxy",
    }


def quota_proxy_report(root: Path) -> dict[str, object]:
    conn = connect(database_path(root))
    row = conn.execute("select coalesce(sum(stdout_bytes + stderr_bytes),0) from commands").fetchone()
    raw = int(row[0] or 0)
    metrics = dict(conn.execute("select key, value from metrics").fetchall())
    compact = int(metrics.get("compact_output_bytes", 0))
    saved_bytes = max(0, raw - compact)
    tokens_saved = saved_bytes // 4
    reduction_percent = round((saved_bytes / raw) * 100, 2) if raw else 0.0
    api = estimate_api_cost(tokens_saved)
    return {
        "tokens_saved_estimate": tokens_saved,
        "reduction_percent": reduction_percent,
        "subscription_quota_multiplier_verified": False,
        "note": "Codex subscription quota mapping is not exposed by the host; values are API-cost proxies only.",
        **api,
    }