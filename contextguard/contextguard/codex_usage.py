from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable


LONG_CONTEXT_THRESHOLD = 272_000
PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing"

# Standard API prices in USD per one million tokens, published 2026-07-22.
MODEL_PRICES = {
    "gpt-5.6-sol": {
        "short": {"input": 5.0, "cached_input": 0.5, "cache_write": 6.25, "output": 30.0},
        "long": {"input": 10.0, "cached_input": 1.0, "cache_write": 12.5, "output": 45.0},
    },
    "gpt-5.6-terra": {
        "short": {"input": 2.5, "cached_input": 0.25, "cache_write": 3.125, "output": 15.0},
        "long": {"input": 5.0, "cached_input": 0.5, "cache_write": 6.25, "output": 22.5},
    },
    "gpt-5.6-luna": {
        "short": {"input": 1.0, "cached_input": 0.1, "cache_write": 1.25, "output": 6.0},
        "long": {"input": 2.0, "cached_input": 0.2, "cache_write": 2.5, "output": 9.0},
    },
    # Kept for mixed or older traces; new estimates default to GPT-5.6 Sol.
    "gpt-5.5": {
        "short": {"input": 5.0, "cached_input": 0.5, "cache_write": 5.0, "output": 30.0},
        "long": {"input": 10.0, "cached_input": 1.0, "cache_write": 10.0, "output": 45.0},
    },
    "gpt-5.4-mini": {
        "short": {"input": 0.75, "cached_input": 0.075, "cache_write": 0.75, "output": 4.5},
        "long": {"input": 0.75, "cached_input": 0.075, "cache_write": 0.75, "output": 4.5},
    },
}

TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


def canonical_model(model: str | None) -> str:
    value = (model or "unknown").lower()
    for known in MODEL_PRICES:
        if value == known or value.startswith(known + "-"):
            return known
    return value


def _tokens(usage: object) -> dict[str, int]:
    data = usage if isinstance(usage, dict) else {}
    return {field: max(0, int(data.get(field, 0) or 0)) for field in TOKEN_FIELDS}


def calculate_turn_cost(model: str, usage: dict[str, int]) -> tuple[float | None, str]:
    prices = MODEL_PRICES.get(canonical_model(model))
    context_class = "long" if usage["input_tokens"] > LONG_CONTEXT_THRESHOLD else "short"
    if prices is None:
        return None, context_class
    rate = prices[context_class]
    cached = min(usage["input_tokens"], usage["cached_input_tokens"])
    cache_write = min(max(0, usage["input_tokens"] - cached), usage["cache_write_input_tokens"])
    uncached = max(0, usage["input_tokens"] - cached - cache_write)
    cost = (
        uncached * rate["input"]
        + cached * rate["cached_input"]
        + cache_write * rate["cache_write"]
        + usage["output_tokens"] * rate["output"]
    ) / 1_000_000
    return cost, context_class


def parse_codex_session(path: Path) -> dict[str, object]:
    model = "unknown"
    effort = None
    session_id = None
    session_cwd = None
    previous_total: tuple[int, ...] | None = None
    breakdown: dict[str, dict[str, object]] = {}
    malformed_lines = 0

    try:
        handle = path.open(encoding="utf-8")
    except OSError as exc:
        return {"available": False, "error": str(exc), "source": str(path)}

    with handle:
        for line in handle:
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                malformed_lines += 1
                continue
            event_type = event.get("type")
            payload = event.get("payload") or {}
            if event_type == "session_meta":
                session_id = payload.get("id") or session_id
                session_cwd = payload.get("cwd") or session_cwd
                model = payload.get("model") or model
                continue
            if event_type == "turn_context":
                model = payload.get("model") or model
                effort = payload.get("effort") or effort
                continue
            if event_type != "event_msg" or payload.get("type") != "token_count":
                continue

            info = payload.get("info") or {}
            total = _tokens(info.get("total_token_usage"))
            total_key = tuple(total[field] for field in TOKEN_FIELDS)
            if total_key == previous_total:
                continue
            last = _tokens(info.get("last_token_usage"))
            if not any(last.values()) and previous_total is not None:
                last = {
                    field: max(0, total[field] - previous_total[index])
                    for index, field in enumerate(TOKEN_FIELDS)
                }
            previous_total = total_key
            if not any(last.values()):
                continue

            model_name = canonical_model(model)
            bucket = breakdown.setdefault(
                model_name,
                {
                    "model": model_name,
                    "reasoning_effort": effort,
                    "turns": 0,
                    **{field: 0 for field in TOKEN_FIELDS},
                    "short_context_turns": 0,
                    "long_context_turns": 0,
                    "api_cost_usd": 0.0,
                    "cost_available": model_name in MODEL_PRICES,
                },
            )
            bucket["reasoning_effort"] = effort or bucket.get("reasoning_effort")
            bucket["turns"] = int(bucket["turns"]) + 1
            for field in TOKEN_FIELDS:
                bucket[field] = int(bucket[field]) + last[field]
            cost, context_class = calculate_turn_cost(model_name, last)
            bucket[f"{context_class}_context_turns"] = int(bucket[f"{context_class}_context_turns"]) + 1
            if cost is None:
                bucket["cost_available"] = False
            else:
                bucket["api_cost_usd"] = float(bucket["api_cost_usd"]) + cost

    models = []
    totals = {field: 0 for field in TOKEN_FIELDS}
    exact_cost = 0.0
    cost_complete = bool(breakdown)
    for bucket in breakdown.values():
        bucket["api_cost_usd"] = round(float(bucket["api_cost_usd"]), 6)
        models.append(bucket)
        for field in TOKEN_FIELDS:
            totals[field] += int(bucket[field])
        exact_cost += float(bucket["api_cost_usd"])
        cost_complete = cost_complete and bool(bucket["cost_available"])

    return {
        "available": bool(models),
        "session_id": session_id,
        "session_cwd": session_cwd,
        "source": str(path),
        "models_used": [bucket["model"] for bucket in models],
        "model_breakdown": models,
        **totals,
        "api_cost_usd": round(exact_cost, 6) if cost_complete else None,
        "api_cost_complete": cost_complete,
        "pricing_basis": "OpenAI standard API, per-turn short/long context",
        "pricing_source": PRICING_SOURCE,
        "malformed_lines": malformed_lines,
        "note": "API-equivalent local trace cost; Codex subscription billing and service-tier uplifts are not exposed.",
    }


def _session_files(codex_home: Path) -> Iterable[Path]:
    for directory in (codex_home / "sessions", codex_home / "archived_sessions"):
        if directory.is_dir():
            yield from directory.rglob("*.jsonl")


def _session_matches_root(path: Path, root: Path) -> bool:
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                event = json.loads(line)
                if event.get("type") != "session_meta":
                    continue
                cwd = (event.get("payload") or {}).get("cwd")
                if not cwd:
                    return False
                resolved_cwd = Path(cwd).resolve()
                resolved_root = root.resolve()
                return (
                    resolved_cwd == resolved_root
                    or resolved_root in resolved_cwd.parents
                    or resolved_cwd in resolved_root.parents
                )
    except (OSError, json.JSONDecodeError):
        return False
    return False


def find_current_codex_session(root: Path, *, codex_home: Path | None = None) -> Path | None:
    home = codex_home or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    candidates = sorted(
        _session_files(home),
        key=lambda item: item.stat().st_mtime if item.exists() else 0,
        reverse=True,
    )
    return next((path for path in candidates if _session_matches_root(path, root)), None)


def current_codex_usage(root: Path, *, codex_home: Path | None = None) -> dict[str, object]:
    path = find_current_codex_session(root, codex_home=codex_home)
    if path is None:
        return {
            "available": False,
            "models_used": [],
            "api_cost_usd": None,
            "note": "No local Codex session trace matched this project.",
        }
    return parse_codex_session(path)
