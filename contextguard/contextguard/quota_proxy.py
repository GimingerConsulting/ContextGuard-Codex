from __future__ import annotations

from pathlib import Path

from .config import database_path
from .codex_usage import MODEL_PRICES, PRICING_LAST_VERIFIED, PRICING_SOURCE, canonical_model
from .database import connect


DEFAULT_MIX = {
    "cached_input_share": 0.88,
    "uncached_input_share": 0.08,
    "output_share": 0.04,
}

GPT56_SOL_RATES = {
    "uncached_input_per_m": 4.0,
    "cached_input_per_m": 0.4,
    "output_per_m": 20.0,
}

DEFAULT_PROXY_MODEL = "gpt-5.6-sol"
MODEL_LABELS = {
    "gpt-6-astra": "GPT-6 Astra",
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna",
}


def estimate_api_cost(
    tokens_saved: int,
    *,
    model: str = DEFAULT_PROXY_MODEL,
    savings_share: float = 0.41,
) -> dict[str, object]:
    selected_model = canonical_model(model)
    prices = MODEL_PRICES.get(selected_model, {}).get("short")
    if prices is None:
        selected_model = DEFAULT_PROXY_MODEL
        prices = MODEL_PRICES[selected_model]["short"]
    gross_tokens = tokens_saved / savings_share if savings_share else 0.0
    saved_cost = (
        gross_tokens
        * DEFAULT_MIX["uncached_input_share"]
        * prices["input"]
        / 1_000_000
    )
    saved_cost += (
        gross_tokens
        * DEFAULT_MIX["cached_input_share"]
        * prices["cached_input"]
        / 1_000_000
    )
    saved_cost += (
        gross_tokens
        * DEFAULT_MIX["output_share"]
        * prices["output"]
        / 1_000_000
    ) * 0.2
    return {
        "estimated_gross_tokens": round(gross_tokens),
        "estimated_monthly_api_savings_usd": round(saved_cost * 30, 2),
        "estimated_daily_api_savings_usd": round(saved_cost, 4),
        "pricing_model": f"{MODEL_LABELS.get(selected_model, selected_model)} proxy",
        "model": selected_model,
        "pricing_basis": "OpenAI standard API short-context proxy; cached/uncached/output mix is estimated",
        "pricing_source": PRICING_SOURCE,
        "pricing_last_verified": PRICING_LAST_VERIFIED,
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
