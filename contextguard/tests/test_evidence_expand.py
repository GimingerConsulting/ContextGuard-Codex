from pathlib import Path

from contextguard.evidence_expand import build_evidence_expand_directive, expand_from_evidence
from contextguard.session_state import record_evidence, reset_session_state


def test_expand_directive_points_to_inspect_window(tmp_path: Path):
    reset_session_state(tmp_path)
    target = tmp_path / "pkg" / "service.py"
    target.parent.mkdir()
    target.write_text("\n".join(f"line {i}" for i in range(1, 41)) + "\n", encoding="utf-8")
    record_evidence(
        tmp_path,
        "abc123",
        "/tmp/summary.json",
        locations=["pkg/service.py:25"],
        failed_tests=["tests/test_service.py::test_case"],
    )

    directive = build_evidence_expand_directive(tmp_path, "abc123")

    assert "inspect pkg/service.py" in directive
    assert "failed_tests" in directive


def test_expand_from_evidence_returns_bounded_window(tmp_path: Path):
    reset_session_state(tmp_path)
    target = tmp_path / "pkg" / "service.py"
    target.parent.mkdir()
    target.write_text("\n".join(f"line {i}" for i in range(1, 41)) + "\n", encoding="utf-8")
    record_evidence(tmp_path, "fp1", "/tmp/summary.json", locations=["pkg/service.py:25"])

    result = expand_from_evidence(tmp_path, "fp1")

    assert result["ok"] is True
    assert "window" in result["result"]
    assert "line 25" in result["result"]["window"]["content"]