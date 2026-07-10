from contextguard.cross_session import (
    load_cross_session_summary,
    persist_cross_session_summary,
    render_cross_session_brief,
)
from contextguard.onboarding import initialize_project
from contextguard.session_state import persist_checkpoint, reset_session_state


def test_persist_and_render_cross_session_brief(tmp_path):
    initialize_project(tmp_path)
    reset_session_state(tmp_path)
    persist_checkpoint(
        tmp_path,
        {
            "current_objective": "ship tier features",
            "likely_relevant_files": ["contextguard/cli.py"],
            "verified_tests": ["171 passed"],
        },
    )
    persist_cross_session_summary(tmp_path)
    summary = load_cross_session_summary(tmp_path)
    assert summary["checkpoint"]["current_objective"] == "ship tier features"
    brief = render_cross_session_brief(tmp_path)
    assert "prior-session resume" in brief
    assert "ship tier features" in brief