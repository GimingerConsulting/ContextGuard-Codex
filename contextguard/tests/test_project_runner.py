from __future__ import annotations

import subprocess
from pathlib import Path

from contextguard.project_runner import install_project_runner, project_runner_ready, runtime_path


def test_project_runner_uses_project_local_runtime(tmp_path: Path):
    runner = install_project_runner(tmp_path)
    runtime = runtime_path(tmp_path)

    assert (runtime / "contextguard" / "cli.py").is_file()
    assert str(runtime) in runner.read_text(encoding="utf-8")
    assert project_runner_ready(tmp_path) is True

    result = subprocess.run(
        [str(runner), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "contextguard" in result.stdout


def test_project_runner_refresh_replaces_stale_runtime(tmp_path: Path):
    install_project_runner(tmp_path)
    stale = runtime_path(tmp_path) / "contextguard" / "stale.py"
    stale.write_text("STALE = True\n", encoding="utf-8")

    install_project_runner(tmp_path)

    assert not stale.exists()
