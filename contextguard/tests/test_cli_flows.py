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
