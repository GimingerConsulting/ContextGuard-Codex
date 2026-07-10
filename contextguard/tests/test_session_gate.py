from pathlib import Path

from contextguard.onboarding import initialize_project
from contextguard.session_gate import build_session_gate


def test_session_gate_includes_brief_and_policy(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    initialize_project(tmp_path)
    gate = build_session_gate(tmp_path, include_surface=False)
    assert "session gate" in gate.lower()
    assert "ARCHITECTURE.md" in gate or "canonical=docs/ARCHITECTURE.md" in gate
    assert "capture" in gate