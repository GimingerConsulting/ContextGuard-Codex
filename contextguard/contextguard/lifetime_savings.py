from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import database_path, state_dir
from .database import connect, increment
from .quota_proxy import estimate_api_cost
from .session_state import load_session_state


LIFETIME_FILE = "lifetime.json"
METRIC_KEYS = (
    "lifetime_sessions",
    "lifetime_tokens_saved",
    "lifetime_tokens_added",
    "lifetime_capture_events",
    "lifetime_brief_events",
    "lifetime_expand_events",
    "lifetime_inspect_events",
    "lifetime_commands",
)


def _lifetime_path(root: Path) -> Path:
    return state_dir(root) / "sessions" / LIFETIME_FILE


def _empty_lifetime() -> dict[str, int]:
    return {
        "lifetime_sessions": 0,
        "lifetime_tokens_saved": 0,
        "lifetime_tokens_added": 0,
        "lifetime_capture_events": 0,
        "lifetime_brief_events": 0,
        "lifetime_expand_events": 0,
        "lifetime_inspect_events": 0,
        "lifetime_commands": 0,
    }


def load_lifetime(root: Path) -> dict[str, object]:
    path = _lifetime_path(root)
    if not path.exists():
        return {"version": 1, "updated_at": None, "last_session_flushed": None, "totals": _empty_lifetime()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "updated_at": None, "last_session_flushed": None, "totals": _empty_lifetime()}
    totals = data.get("totals") if isinstance(data, dict) else {}
    if not isinstance(totals, dict):
        totals = _empty_lifetime()
    merged = _empty_lifetime()
    merged.update({key: int(totals.get(key, 0)) for key in METRIC_KEYS})
    return {
        "version": 1,
        "updated_at": data.get("updated_at") if isinstance(data, dict) else None,
        "last_session_flushed": data.get("last_session_flushed") if isinstance(data, dict) else None,
        "totals": merged,
    }


def _write_lifetime(root: Path, totals: dict[str, int], *, last_session_flushed: str | None) -> None:
    path = _lifetime_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_session_flushed": last_session_flushed,
        "totals": totals,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    conn = connect(database_path(root))
    for key in METRIC_KEYS:
        conn.execute(
            "insert or replace into metrics(key, value) values(?, ?)",
            (key, int(totals.get(key, 0))),
        )
    conn.commit()


def flush_session_to_lifetime(root: Path) -> dict[str, object]:
    state = load_session_state(root)
    started_at = state.get("started_at")
    lifetime = load_lifetime(root)
    if started_at and lifetime.get("last_session_flushed") == started_at:
        return {"flushed": False, "reason": "already_flushed"}
    ledger = state.get("ledger") or {}
    ledger_totals = state.get("ledger_totals") or {}
    command_count = len(state.get("commands", []))
    if not ledger and not ledger_totals and command_count == 0:
        return {"flushed": False, "reason": "empty_session"}

    totals = dict(lifetime["totals"])
    totals["lifetime_sessions"] = int(totals.get("lifetime_sessions", 0)) + 1
    totals["lifetime_tokens_saved"] = int(totals.get("lifetime_tokens_saved", 0)) + int(
        ledger_totals.get("tokens_saved", 0)
    )
    totals["lifetime_tokens_added"] = int(totals.get("lifetime_tokens_added", 0)) + int(
        ledger_totals.get("tokens_added", 0)
    )
    totals["lifetime_capture_events"] = int(totals.get("lifetime_capture_events", 0)) + int(
        ledger.get("capture", 0)
    )
    totals["lifetime_brief_events"] = int(totals.get("lifetime_brief_events", 0)) + int(
        ledger.get("brief", 0)
    ) + int(ledger.get("surface_brief", 0))
    totals["lifetime_expand_events"] = int(totals.get("lifetime_expand_events", 0)) + int(
        ledger.get("expand", 0)
    )
    totals["lifetime_inspect_events"] = int(totals.get("lifetime_inspect_events", 0)) + int(
        ledger.get("inspect", 0)
    )
    totals["lifetime_commands"] = int(totals.get("lifetime_commands", 0)) + command_count

    _write_lifetime(root, totals, last_session_flushed=started_at)

    net_saved = max(
        0,
        int(totals["lifetime_tokens_saved"]) - int(totals["lifetime_tokens_added"]),
    )
    return {
        "flushed": True,
        "session_commands": command_count,
        "lifetime_sessions": totals["lifetime_sessions"],
        "lifetime_net_tokens_saved": net_saved,
    }


def lifetime_savings_report(root: Path) -> dict[str, object]:
    lifetime = load_lifetime(root)
    totals = lifetime["totals"]
    conn = connect(database_path(root))
    command_row = conn.execute("select count(*), coalesce(sum(stdout_bytes + stderr_bytes),0) from commands").fetchone()
    metrics = dict(conn.execute("select key, value from metrics").fetchall())
    raw_bytes = int(command_row[1] or 0)
    compact = int(metrics.get("compact_output_bytes", 0))
    capture_saved_bytes = max(0, raw_bytes - compact)

    lifetime_tokens_saved = int(totals.get("lifetime_tokens_saved", 0))
    lifetime_tokens_added = int(totals.get("lifetime_tokens_added", 0))
    ledger_net = max(0, lifetime_tokens_saved - lifetime_tokens_added)
    capture_tokens_saved = capture_saved_bytes // 4
    combined_net_saved = max(ledger_net, capture_tokens_saved)

    api = estimate_api_cost(combined_net_saved)
    return {
        "lifetime_sessions": int(totals.get("lifetime_sessions", 0)),
        "lifetime_commands": int(totals.get("lifetime_commands", 0)),
        "lifetime_capture_events": int(totals.get("lifetime_capture_events", 0)),
        "lifetime_brief_events": int(totals.get("lifetime_brief_events", 0)),
        "lifetime_expand_events": int(totals.get("lifetime_expand_events", 0)),
        "lifetime_inspect_events": int(totals.get("lifetime_inspect_events", 0)),
        "lifetime_tokens_saved_estimate": lifetime_tokens_saved,
        "lifetime_tokens_added_estimate": lifetime_tokens_added,
        "lifetime_net_tokens_saved_estimate": ledger_net,
        "lifetime_capture_tokens_saved_estimate": capture_tokens_saved,
        "lifetime_combined_net_tokens_saved_estimate": combined_net_saved,
        "estimated_lifetime_api_savings_usd": api["estimated_daily_api_savings_usd"],
        "estimated_lifetime_api_savings_usd_monthly": api["estimated_monthly_api_savings_usd"],
        "pricing_model": api["pricing_model"],
        "updated_at": lifetime.get("updated_at"),
        "note": "Lifetime totals accumulate across Codex sessions when a session ends or a new one starts.",
    }