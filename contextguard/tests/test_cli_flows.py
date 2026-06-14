import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(args: list[str], cwd: Path):
    return subprocess.run(
        [sys.executable, "-m", "contextguard.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
    )


def test_init_repeated_status_and_paths_with_spaces(tmp_path: Path):
    project = tmp_path / "project with spaces"
    project.mkdir()
    (project / "package.json").write_text('{"scripts":{"test":"echo ok"}}\n')
    first = run_cli(["init"], project)
    second = run_cli(["init"], project)
    status = run_cli(["status"], project)
    assert first.returncode == 0
    assert second.returncode == 0
    assert status.returncode == 0
    assert "ContextGuard: active" in status.stdout
    assert "Last refresh: unknown" not in status.stdout
    assert "Lifetime estimated tokens saved:" in status.stdout
    assert "Lifetime context reduction:" in status.stdout
    assert (project / ".contextguard" / "index.sqlite").exists()
    runner = project / ".contextguard" / "bin" / "contextguard"
    assert runner.exists()
    assert runner.stat().st_mode & 0o111
    runner_status = subprocess.run(
        [str(runner), "status"],
        cwd=project,
        text=True,
        capture_output=True,
    )
    assert runner_status.returncode == 0
    assert "Execution protection: ready" in runner_status.stdout


def test_setup_initializes_empty_project_and_explains_unverified_hooks(tmp_path: Path):
    result = run_cli(["setup"], tmp_path)
    second = run_cli(["setup"], tmp_path)

    assert result.returncode == 0
    assert second.returncode == 0
    assert "ContextGuard setup complete" in result.stdout
    assert "Project: initialized" in result.stdout
    assert "Hook status: not yet observed" in result.stdout
    assert "/hooks" in result.stdout
    assert "Execution protection: ready" in result.stdout
    assert "works without hook output replacement" in result.stdout
    assert "Project kind: empty" in second.stdout
    assert (tmp_path / ".contextguard" / "manifest.json").exists()


def test_setup_preserves_existing_instructions_and_is_idempotent(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Existing\n\nKeep this rule.\n")
    (tmp_path / "app.py").write_text("VALUE = 1\n")

    first = run_cli(["setup"], tmp_path)
    second = run_cli(["setup"], tmp_path)

    assert first.returncode == 0
    assert second.returncode == 0
    assert "Keep this rule." in agents.read_text()
    assert agents.read_text().count("BEGIN CONTEXTGUARD MANAGED SECTION") == 1


def test_refresh_reuses_unchanged_index_entries(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('ok')\n")
    run_cli(["init"], tmp_path)
    run_cli(["refresh"], tmp_path)
    report = run_cli(["report"], tmp_path)
    assert "cache_hits:" in report.stdout
    assert "repeated_reads_avoided:" in report.stdout


def test_capture_preserves_non_zero_exit_code(tmp_path: Path):
    result = run_cli(["capture", "--", sys.executable, "-c", "print('bad'); raise SystemExit(7)"], tmp_path)
    assert result.returncode == 7
    assert result.stdout == "bad\n"
    assert list((tmp_path / ".contextguard" / "tmp").glob("*.summary.json"))


def test_capture_compacts_medium_noisy_test_output(tmp_path: Path):
    script = tmp_path / "noisy.py"
    script.write_text(
        "for i in range(80): print(f'FAILED test_case_{i} file.py:{i}: error')\n"
        "raise SystemExit(1)\n"
    )
    result = run_cli(["capture", "--", sys.executable, str(script)], tmp_path)
    assert result.returncode == 1
    assert "ContextGuard capture summary" in result.stdout
    assert "raw_bytes:" in result.stdout
    assert len(result.stdout.encode()) < 1800


def test_capture_runner_emits_budget_advice_without_hooks(tmp_path: Path):
    run_cli(["init"], tmp_path)
    command = ["capture", "--", sys.executable, "-m", "pytest", "-q"]
    run_cli(command, tmp_path)
    second = run_cli(command, tmp_path)

    assert "two full validations have now run" in second.stdout
    assert "targeted tests" in second.stdout


def test_capture_references_repeated_equivalent_evidence(tmp_path: Path):
    run_cli(["init"], tmp_path)
    command = [
        "capture",
        "--",
        sys.executable,
        "-c",
        "for _ in range(200): print('ERROR stable failure signature')\nraise SystemExit(1)",
    ]

    first = run_cli(command, tmp_path)
    second = run_cli(command, tmp_path)

    assert first.returncode == second.returncode == 1
    assert "unique_errors:" in first.stdout
    assert "ContextGuard repeated evidence" in second.stdout
    assert "unique_errors:" not in second.stdout
    assert len(second.stdout.encode()) < len(first.stdout.encode())


def test_capture_unexplained_failure_requests_bounded_escalation(tmp_path: Path):
    result = run_cli(
        [
            "capture",
            "--",
            sys.executable,
            "-c",
            "print('x' * 5000)\nraise SystemExit(3)",
        ],
        tmp_path,
    )

    assert result.returncode == 3
    assert "escalation: failed_without_diagnostic" in result.stdout
    assert "bounded slice" in result.stdout
    assert len(result.stdout.encode()) < 1400


def test_project_runner_capture_compacts_before_output_reaches_host(tmp_path: Path):
    project = tmp_path / "runner project"
    project.mkdir()
    run_cli(["setup"], project)
    script = project / "noisy.py"
    script.write_text(
        "for i in range(130): print(f'FAILED tests/test_live.py::test_{i} - AssertionError')\n"
        "print('130 failed in 0.50s')\n"
        "raise SystemExit(1)\n"
    )

    runner = project / ".contextguard" / "bin" / "contextguard"
    result = subprocess.run(
        [str(runner), "capture", "--", sys.executable, str(script)],
        cwd=project,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "ContextGuard capture summary" in result.stdout
    assert "130 failed in 0.50s" in result.stdout
    assert len(result.stdout.encode()) < 2200
    assert list((project / ".contextguard" / "tmp").glob("*.stdout.txt"))


def test_refresh_regenerates_missing_project_runner(tmp_path: Path):
    run_cli(["init"], tmp_path)
    runner = tmp_path / ".contextguard" / "bin" / "contextguard"
    runner.unlink()

    result = run_cli(["refresh"], tmp_path)

    assert result.returncode == 0
    assert runner.exists()
    assert runner.stat().st_mode & 0o111


def test_report_shows_visible_lifetime_savings(tmp_path: Path):
    run_cli(["init"], tmp_path)
    run_cli(
        [
            "capture",
            "--",
            sys.executable,
            "-c",
            "for i in range(80): print('ERROR repeated failure line', i)",
        ],
        tmp_path,
    )
    result = run_cli(["report"], tmp_path)
    assert result.returncode == 0
    assert "estimated_tokens_saved:" in result.stdout
    assert "estimated_reduction_percent:" in result.stdout


def test_uninstall_requires_confirmation(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    run_cli(["init"], project)
    dry = run_cli(["uninstall-project"], project)
    assert dry.returncode == 0
    assert (project / ".contextguard").exists()
    confirmed = run_cli(["uninstall-project", "--yes"], project)
    assert confirmed.returncode == 0
    assert not (project / ".contextguard").exists()
