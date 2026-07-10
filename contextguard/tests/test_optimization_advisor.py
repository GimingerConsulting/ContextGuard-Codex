from pathlib import Path

from contextguard.optimization_advisor import analyze_command, record_command
from contextguard.session_state import reset_session_state


def test_exact_unchanged_read_is_advised_once(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("print('ok')\n")
    reset_session_state(tmp_path)

    record_command(tmp_path, "sed -n '1,40p' app.py", succeeded=True)
    first = analyze_command(tmp_path, "sed -n '1,40p' app.py")
    second = analyze_command(tmp_path, "sed -n '1,40p' app.py")

    assert "unchanged" in first.lower()
    assert second == ""


def test_changed_file_invalidates_read_reuse(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("first\n")
    reset_session_state(tmp_path)
    record_command(tmp_path, "cat app.py", succeeded=True)

    target.write_text("second\n")

    assert analyze_command(tmp_path, "cat app.py") == ""


def test_unsupported_or_missing_reads_are_not_cached(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "python3 inspect.py", succeeded=True)
    record_command(tmp_path, "cat missing.py", succeeded=True)

    assert analyze_command(tmp_path, "python3 inspect.py") == ""
    assert analyze_command(tmp_path, "cat missing.py") == ""


def test_repeated_repository_listing_gets_grouping_advice(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "rg --files", succeeded=True)

    advice = analyze_command(tmp_path, "rg --files")

    assert "repository listing" in advice.lower()


def test_two_full_validations_are_allowed_but_third_is_advised(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "python3 -m pytest -q", succeeded=True)
    assert analyze_command(tmp_path, "python3 -m pytest -q") == ""
    record_command(tmp_path, "python3 -m pytest -q", succeeded=True)

    advice = analyze_command(tmp_path, "python3 -m pytest -q")

    assert "full validation" in advice.lower()


def test_repeated_repository_checks_get_grouping_advice(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "git status --short", succeeded=True)
    record_command(tmp_path, "git diff --check", succeeded=True)

    advice = analyze_command(tmp_path, "git status --short")

    assert "repository checks" in advice.lower()


def test_targeted_tests_do_not_consume_full_validation_budget(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "pytest -q tests/test_app.py::test_value", succeeded=True)
    record_command(tmp_path, "pytest -q tests/test_app.py::test_other", succeeded=True)

    assert analyze_command(tmp_path, "pytest -q tests/test_app.py::test_third") == ""


def test_failed_full_validations_still_consume_command_budget(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "pytest -q", succeeded=False)
    record_command(tmp_path, "pytest -q", succeeded=False)

    assert "full validation" in analyze_command(tmp_path, "pytest -q").lower()


def test_command_milestone_advice_is_deduplicated(tmp_path: Path):
    reset_session_state(tmp_path)
    for index in range(12):
        record_command(tmp_path, f"printf {index}", succeeded=True)

    first = analyze_command(tmp_path, "printf next")
    second = analyze_command(tmp_path, "printf next")

    assert "10 commands" in first
    assert second == ""


def test_three_searches_trigger_named_file_next_action(tmp_path: Path):
    reset_session_state(tmp_path)
    record_command(tmp_path, "rg -n alpha contextguard", succeeded=True)
    record_command(tmp_path, "rg -n beta tests", succeeded=True)
    record_command(tmp_path, "rg -n gamma docs", succeeded=True)

    advice = analyze_command(tmp_path, "rg -n delta .")

    assert "three searches" in advice.lower()
    assert "named file" in advice.lower()
