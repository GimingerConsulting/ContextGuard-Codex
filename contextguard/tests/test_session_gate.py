from pathlib import Path

from contextguard.onboarding import initialize_project
from contextguard.session_gate import build_session_gate
from contextguard.context_capsule import persist_session_capsule


def test_session_gate_includes_brief_and_policy(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    initialize_project(tmp_path)
    gate = build_session_gate(tmp_path, include_surface=False)
    assert "session gate" in gate.lower()
    assert "ARCHITECTURE.md" in gate or "canonical=docs/ARCHITECTURE.md" in gate
    assert "capture" in gate


def test_session_gate_keeps_static_prefix_stable_when_objective_changes(tmp_path: Path):
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    initialize_project(tmp_path)
    persist_session_capsule(tmp_path, {"current_objective": "first objective"})
    first = build_session_gate(tmp_path, include_surface=False)
    persist_session_capsule(tmp_path, {"current_objective": "second objective"})
    second = build_session_gate(tmp_path, include_surface=False)

    marker = "ContextGuard dynamic session state:"
    assert first.split(marker)[0] == second.split(marker)[0]
    assert "first objective" in first
    assert "second objective" in second
