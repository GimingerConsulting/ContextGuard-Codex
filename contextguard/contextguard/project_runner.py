from __future__ import annotations

import shlex
import shutil
import sys
import os
from pathlib import Path

from .config import state_dir


def runner_path(root: Path) -> Path:
    return state_dir(root) / "bin" / "contextguard"


def runtime_path(root: Path) -> Path:
    return state_dir(root) / "runtime"


def _install_runtime(root: Path) -> Path:
    source_package = Path(__file__).resolve().parent
    destination = runtime_path(root)
    temporary = destination.with_name(f"{destination.name}.{os.getpid()}.tmp")
    previous = destination.with_name(f"{destination.name}.{os.getpid()}.old")
    shutil.rmtree(temporary, ignore_errors=True)
    shutil.rmtree(previous, ignore_errors=True)
    temporary.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_package,
        temporary / "contextguard",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    if destination.exists():
        destination.replace(previous)
    temporary.replace(destination)
    shutil.rmtree(previous, ignore_errors=True)
    return destination


def install_project_runner(root: Path) -> Path:
    path = runner_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    package_root = _install_runtime(root)
    bootstrap = (
        "import sys; "
        f"sys.path.insert(0, {package_root.as_posix()!r}); "
        "from contextguard.cli import main; "
        "raise SystemExit(main())"
    )
    content = (
        "#!/bin/sh\n"
        f"exec {shlex.quote(sys.executable)} -c {shlex.quote(bootstrap)} \"$@\"\n"
    )
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


def project_runner_ready(root: Path) -> bool:
    path = runner_path(root)
    runtime_cli = runtime_path(root) / "contextguard" / "cli.py"
    return path.is_file() and bool(path.stat().st_mode & 0o111) and runtime_cli.is_file()
