from pathlib import Path

from contextguard import output_capture
from contextguard.command_classifier import classify_command
from contextguard.command_rewriter import rewrite_for_capture, rewrite_for_inspect
from contextguard.onboarding import initialize_project
from contextguard.session_state import record_working_set
from contextguard.utils import sha256_file


def test_advice_does_not_force_small_output_compaction(tmp_path: Path):
    initialize_project(tmp_path)

    summary = {"errors": [], "line_count": 1}

    assert output_capture._should_compact_capture(
        summary,
        80,
        tmp_path,
        repeated_output={"repeated": False},
    ) is False


def test_compaction_requires_visible_savings():
    assert output_capture._compaction_is_cost_safe(1000, "x" * 700) is True
    assert output_capture._compaction_is_cost_safe(1000, "x" * 800) is False


def test_targeted_and_full_validation_are_captured_for_cost_safe_logs():
    assert classify_command("pytest -q tests/test_app.py::test_ok").action == "capture"
    assert classify_command("python3 -m pytest -q tests/test_app.py").action == "capture"
    assert classify_command("python3 -m pytest -q").action == "capture"


def test_unverified_source_read_fails_open_after_initialization(tmp_path: Path):
    initialize_project(tmp_path)
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    runner = Path("/plugin/scripts/contextguard")

    assert rewrite_for_inspect("cat app.py", tmp_path, runner) is None
    assert rewrite_for_capture("cat app.py", runner, root=tmp_path) is None


def test_verified_unchanged_source_can_use_snapshot(tmp_path: Path):
    initialize_project(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    record_working_set(tmp_path, f"- implementation app.py sha={sha256_file(source)[:12]}\n")

    rewritten = rewrite_for_inspect("cat app.py", tmp_path, Path("/plugin/scripts/contextguard"))

    assert rewritten is not None
    assert "snapshot app.py" in rewritten
