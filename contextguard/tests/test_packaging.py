import subprocess
import sys
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_builds_wheel_with_contextguard_and_benchmark_packages(tmp_path: Path):
    source = tmp_path / "source"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns(".contextguard", ".pytest_cache", "__pycache__", "build", "*.egg-info"),
    )
    output = tmp_path / "dist"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(output),
            str(source),
        ],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert list(output.glob("contextguard-*.whl"))


def test_declared_python_minimum_matches_supported_system_runtime():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'requires-python = ">=3.9"' in pyproject
    assert 'include = ["contextguard*", "benchmarks*"]' in pyproject
