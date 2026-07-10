from contextguard.adaptive_capture import capture_threshold_bytes, session_phase, should_compact
from contextguard.onboarding import initialize_project
from contextguard.optimization_advisor import record_command
from contextguard.session_state import reset_session_state


def test_onboarding_phase_uses_higher_threshold(tmp_path):
    initialize_project(tmp_path)
    reset_session_state(tmp_path)
    assert session_phase(tmp_path) == "onboarding"
    assert capture_threshold_bytes(tmp_path) == 4096


def test_debug_phase_lowers_threshold(tmp_path):
    initialize_project(tmp_path)
    reset_session_state(tmp_path)
    for command in ("pytest -q", "rg --files", "git diff", "pytest -q", "pytest -q", "pytest -q", "pytest -q", "pytest -q"):
        record_command(tmp_path, command, succeeded=True)
    assert session_phase(tmp_path) == "debug"
    assert capture_threshold_bytes(tmp_path) == 1024


def test_should_compact_on_errors_before_threshold(tmp_path):
    initialize_project(tmp_path)
    reset_session_state(tmp_path)
    assert should_compact(1200, tmp_path, has_errors=True, line_count=10) is True