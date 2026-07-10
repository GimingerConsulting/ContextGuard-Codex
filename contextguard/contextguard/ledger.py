from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .session_state import load_session_state, save_session_state
from .utils import estimate_tokens


LEDGER_KINDS = (
    "brief",
    "surface_brief",
    "capture",
    "expand",
    "inspect",
    "capsule",
    "advice",
    "passthrough",
)


def _empty_ledger() -> dict[str, int]:
    return {kind: 0 for kind in LEDGER_KINDS}


def record_ledger(
    root: Path,
    kind: str,
    *,
    bytes_added: int = 0,
    bytes_saved: int = 0,
    label: str = "",
) -> None:
    if kind not in LEDGER_KINDS:
        return
    state = load_session_state(root)
    ledger = state.setdefault("ledger", _empty_ledger())
    ledger[kind] = int(ledger.get(kind, 0)) + 1
    totals = state.setdefault("ledger_totals", {"bytes_added": 0, "bytes_saved": 0, "tokens_added": 0, "tokens_saved": 0})
    totals["bytes_added"] = int(totals.get("bytes_added", 0)) + max(0, bytes_added)
    totals["bytes_saved"] = int(totals.get("bytes_saved", 0)) + max(0, bytes_saved)
    totals["tokens_added"] = int(totals.get("tokens_added", 0)) + estimate_tokens("x" * max(0, bytes_added))
    totals["tokens_saved"] = int(totals.get("tokens_saved", 0)) + estimate_tokens("x" * max(0, bytes_saved))
    events = state.setdefault("ledger_events", [])
    events.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "bytes_added": bytes_added,
            "bytes_saved": bytes_saved,
            "label": label,
        }
    )
    state["ledger_events"] = events[-50:]
    save_session_state(root, state)


def ledger_summary(root: Path) -> dict[str, object]:
    state = load_session_state(root)
    ledger = state.get("ledger") or _empty_ledger()
    totals = state.get("ledger_totals") or {}
    return {
        "counts": dict(ledger),
        "totals": dict(totals),
        "routing_locked": bool(state.get("routing_locked")),
        "events": list(state.get("ledger_events") or [])[-10:],
    }