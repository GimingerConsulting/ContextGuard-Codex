import json
from pathlib import Path

from benchmarks.real_codex_support_ab import (
    PROMPT,
    RUN_ORDERS,
    apply_reference_solution,
    build_codex_command,
    build_release_gate,
    create_fixture,
    prepare_optimized_project_with_hooks,
    validate_fixture,
    sol_credit_cost,
    api_cost_usd,
)


def test_support_prompt_is_ticket_driven_without_solution_requirements():
    assert "SUPPORT_TICKET.md" in PROMPT
    assert "reproduce" in PROMPT.lower()
    assert "root cause" in PROMPT.lower()
    assert "threading.RLock" not in PROMPT
    assert "schema version 2" not in PROMPT


def test_three_runs_counterbalance_execution_order():
    assert RUN_ORDERS == [("raw", "contextguard"), ("contextguard", "raw"), ("raw", "contextguard")]


def test_hidden_acceptance_fails_before_fix_and_passes_reference(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")
    before = validate_fixture(project)
    assert before["exit_code"] != 0
    assert before["hidden_failed_tests"] > 0

    apply_reference_solution(project)
    after = validate_fixture(project)
    assert after["exit_code"] == 0
    assert after["hidden_passed_tests"] == 144
    assert after["canonical_output"]["status"] == "reserved"


def test_agent_repository_does_not_contain_hidden_tests(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")
    files = {path.name for path in project.rglob("*.py")}
    assert "test_hidden_acceptance.py" not in files
    assert (project / "SUPPORT_TICKET.md").exists()
    assert not (project / "SPEC.md").exists()


def test_each_trial_uses_a_separate_temporary_root():
    source = (Path(__file__).resolve().parents[1] / "benchmarks/real_codex_support_ab.py").read_text()
    assert 'prefix=f"contextguard-support-ab-{index}-{kind}-"' in source


def test_optimized_fixture_activates_the_same_hooks_as_an_installed_plugin(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")

    prepare_optimized_project_with_hooks(project)

    hooks = json.loads((project / ".codex/hooks.json").read_text())
    command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert "PYTHONPATH=" in command
    assert "$PLUGIN_ROOT" not in command
    assert "user_prompt_submit.py" in command


def test_codex_command_enables_hooks_only_for_contextguard(tmp_path: Path):
    assert "features.plugins=false" in build_codex_command(tmp_path, optimized=False)
    assert "features.plugins=true" in build_codex_command(tmp_path, optimized=True)


def test_release_gate_requires_50_percent_total_savings_and_no_extra_commands():
    pairs = [
        {
            "accepted": True,
            "raw": {"input_tokens": 100, "output_tokens": 20, "command_executions": 4, "usage_event_seen": True},
            "contextguard": {"input_tokens": 45, "output_tokens": 10, "command_executions": 4, "usage_event_seen": True},
        }
        for _ in range(3)
    ]
    aggregate = {
        "total_tokens": {"median_change_percent": -54.17},
        "sol_credits": {"median_change_percent": -52.27},
        "api_cost_usd": {"median_change_percent": -52.27},
    }

    assert build_release_gate(pairs, aggregate)["passed"] is True

    pairs[0]["contextguard"]["command_executions"] = 5
    assert build_release_gate(pairs, aggregate)["passed"] is False


def test_sol_credit_cost_uses_official_cached_input_discount():
    run = {"input_tokens": 1_000_000, "cached_input_tokens": 900_000, "output_tokens": 10_000}

    assert sol_credit_cost(run) == 31.25


def test_api_cost_uses_official_gpt_56_sol_standard_rates():
    run = {"input_tokens": 1_000_000, "cached_input_tokens": 900_000, "output_tokens": 10_000}

    assert api_cost_usd(run) == 1.25
