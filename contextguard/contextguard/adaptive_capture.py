from __future__ import annotations

from pathlib import Path

from .session_state import load_session_state


PHASE_THRESHOLDS = {
    "onboarding": 4096,
    "build": 2048,
    "debug": 1024,
    "validation": 1536,
}


def session_phase(root: Path) -> str:
    state = load_session_state(root)
    families = {item.get("family") for item in state.get("commands", [])}
    if "full_validation" in families or "targeted_validation" in families:
        if "repository_check" in families or len(state.get("commands", [])) >= 8:
            return "debug"
        return "build"
    if len(state.get("commands", [])) <= 2:
        return "onboarding"
    return "build"


def capture_threshold_bytes(root: Path) -> int:
    return PHASE_THRESHOLDS.get(session_phase(root), 2048)


def should_compact(raw_bytes: int, root: Path, *, has_errors: bool = False, line_count: int = 0) -> bool:
    threshold = capture_threshold_bytes(root)
    if raw_bytes >= threshold:
        return True
    if raw_bytes >= 1024 and (has_errors or line_count > 40):
        return True
    return False