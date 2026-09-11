import json
from pathlib import Path

from benchmarks.real_codex_backend_ab import (
    PROMPT,
    apply_reference_solution,
    build_codex_command,
    create_fixture,
    validate_fixture,
)


def test_prompt_requires_realistic_baseline_and_full_validation():
    assert "before editing" in PROMPT
    assert "python3 -m pytest -q" in PROMPT
    assert "migration" in PROMPT.lower()
    assert "concurrent" in PROMPT.lower()
    assert "backward" in PROMPT.lower()


def test_backend_fixture_fails_before_reference_and_passes_after(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")
    before = validate_fixture(project)
    assert before["exit_code"] != 0
    assert before["collected_tests"] >= 300

    apply_reference_solution(project)
    after = validate_fixture(project)
    assert after["exit_code"] == 0
    assert after["failed_tests"] == 0
    assert after["canonical_output"]["status"] == "reserved"
    assert after["canonical_output"]["available"] == 7
    assert after["migration_output"]["schema_version"] == 2
    assert after["concurrency_output"]["successful"] == 10
    assert after["concurrency_output"]["available"] == 0


def test_raw_and_contextguard_commands_use_same_model_prompt_and_settings(tmp_path: Path):
    raw = build_codex_command(tmp_path / "raw", optimized=False)
    optimized = build_codex_command(tmp_path / "optimized", optimized=True)
    assert raw[-1] == optimized[-1] == PROMPT
    assert "gpt-5.5" in raw
    assert 'model_reasoning_effort="medium"' in raw
    assert "features.plugins=false" in raw
    assert "features.plugins=true" in optimized


def test_backend_command_accepts_cost_saving_model_and_effort(tmp_path: Path):
    command = build_codex_command(
        tmp_path / "project",
        optimized=True,
        model="gpt-5.6-luna",
        reasoning_effort="low",
    )
    assert "gpt-5.6-luna" in command
    assert 'model_reasoning_effort="low"' in command


def test_fixture_contains_realistic_repository_noise(tmp_path: Path):
    project = create_fixture(tmp_path / "fixture")
    assert (project / "data/production.log").stat().st_size > 500_000
    assert (project / "data/orders.jsonl").stat().st_size > 500_000
    config = json.loads((project / "legacy-db.json").read_text())
    assert config["schema_version"] == 1
