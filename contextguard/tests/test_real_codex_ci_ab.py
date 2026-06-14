from pathlib import Path

from benchmarks.real_codex_ci_ab import (
    PROMPT,
    RUN_ORDERS,
    apply_reference_solution,
    build_codex_command,
    create_fixture,
    validate_fixture,
)


def test_ci_prompt_requires_normal_investigation_without_solution_hint():
    assert "PR_REVIEW.md" in PROMPT
    assert "CI_FAILURE.log" in PROMPT
    assert "root cause" in PROMPT.lower()
    assert "ZoneInfo" not in PROMPT


def test_ci_runs_are_counterbalanced_and_isolated():
    assert RUN_ORDERS == [("raw", "contextguard"), ("contextguard", "raw")]
    source = (Path(__file__).resolve().parents[1] / "benchmarks/real_codex_ci_ab.py").read_text()
    assert 'prefix=f"contextguard-ci-ab-{index}-{kind}-"' in source


def test_ci_hidden_suite_fails_before_fix_and_passes_reference(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")
    before = validate_fixture(project)
    assert before["public_exit_code"] == 0
    assert before["exit_code"] != 0

    apply_reference_solution(project)
    after = validate_fixture(project)
    assert after["exit_code"] == 0
    assert after["hidden_passed_tests"] == 160
    assert after["canonical_output"]["2026-03-08"] == 2


def test_fixture_looks_like_normal_ci_investigation(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")
    assert (project / "PR_REVIEW.md").exists()
    assert (project / "artifacts/CI_FAILURE.log").stat().st_size > 500_000
    assert not any(path.name == "test_hidden_ci.py" for path in project.rglob("*.py"))


def test_ci_benchmark_model_is_configurable(tmp_path: Path):
    command = build_codex_command(tmp_path, optimized=False, model="gpt-5.4-mini")

    assert command[command.index("--model") + 1] == "gpt-5.4-mini"
