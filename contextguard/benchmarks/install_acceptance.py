#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import tiktoken
except ModuleNotFoundError:
    tiktoken = None


SOURCE_PLUGIN = Path(__file__).resolve().parents[1]
TOKENIZER = tiktoken.get_encoding("o200k_base") if tiktoken else None


def token_count(text: str) -> int:
    if TOKENIZER:
        return len(TOKENIZER.encode(text))
    return (len(text.encode()) + 3) // 4


def install_plugin(destination: Path) -> Path:
    ignored = shutil.ignore_patterns(".git", ".DS_Store", ".pytest_cache", "__pycache__", "*.pyc")
    shutil.copytree(SOURCE_PLUGIN, destination, ignore=ignored)
    return destination


def plugin_environment(plugin: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(plugin)
    return environment


def run_cli(plugin: Path, project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "contextguard.cli", *arguments],
        cwd=project,
        env=plugin_environment(plugin),
        text=True,
        capture_output=True,
    )


def run_hook(plugin: Path, project: Path, hook: str, payload: dict) -> tuple[dict, float]:
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(plugin / "hooks" / hook)],
        cwd=project,
        env=plugin_environment(plugin),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise RuntimeError(f"{hook} failed: {proc.stderr}")
    return json.loads(proc.stdout), elapsed


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_failing_project(project: Path) -> None:
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )
    tests = project / "tests"
    tests.mkdir()
    tests.joinpath("test_hard_output.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.parametrize('index', range(130))\n"
        "def test_hard_failure_matrix(index):\n"
        "    assert index < 0, f'expected negative index, received {index}'\n",
        encoding="utf-8",
    )


def initialize_projects(plugin: Path, root: Path) -> tuple[dict, dict, Path]:
    empty = root / "empty-project"
    empty.mkdir()
    empty_session, _ = run_hook(plugin, empty, "session_start.py", {})
    empty_manifest = json.loads((empty / ".contextguard" / "manifest.json").read_text())

    existing = root / "existing-project"
    existing.mkdir()
    user_agents = "# Existing Instructions\n\nKeep this user-authored rule.\n"
    (existing / "AGENTS.md").write_text(user_agents, encoding="utf-8")
    (existing / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (existing / "service.py").write_text("def run(): return VALUE\n", encoding="utf-8")
    (existing / "README.md").write_text("# Existing Project\n", encoding="utf-8")
    (existing / "pyproject.toml").write_text("[project]\nname = \"existing\"\nversion = \"0.1.0\"\n", encoding="utf-8")
    (existing / "test_app.py").write_text("def test_value(): assert True\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=existing, check=True)
    existing_session, _ = run_hook(plugin, existing, "session_start.py", {})
    existing_manifest = json.loads((existing / ".contextguard" / "manifest.json").read_text())
    existing_agents = (existing / "AGENTS.md").read_text(encoding="utf-8")
    return (
        {
            "initialized": True,
            "automatic_init": "initialized automatically" in json.dumps(empty_session),
            "project_kind": empty_manifest["project_kind"],
            "index_exists": (empty / ".contextguard" / "index.sqlite").exists(),
        },
        {
            "initialized": True,
            "automatic_init": "initialized automatically" in json.dumps(existing_session),
            "project_kind": existing_manifest["project_kind"],
            "user_content_preserved": user_agents.strip() in existing_agents,
            "managed_section_added": "BEGIN CONTEXTGUARD MANAGED SECTION" in existing_agents,
        },
        existing,
    )


def evaluate_hooks(plugin: Path, project: Path, timing_samples: int) -> tuple[dict, dict, dict]:
    session, _ = run_hook(plugin, project, "session_start.py", {})
    prompt, _ = run_hook(
        plugin,
        project,
        "user_prompt_submit.py",
        {"prompt": "Fix the failing hard output tests"},
    )
    pre_tool, _ = run_hook(
        plugin,
        project,
        "pre_tool_use.py",
        {"tool_name": "Bash", "tool_input": {"command": "python3 -m pytest -q"}},
    )

    failing_project = project.parent / "failing-project"
    make_failing_project(failing_project)
    run_cli(plugin, failing_project, "init")
    test_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=failing_project,
        text=True,
        capture_output=True,
    )
    raw_output = test_proc.stdout + test_proc.stderr
    hook_times = []
    post_tool = {}
    for _ in range(timing_samples):
        post_tool, elapsed = run_hook(
            plugin,
            failing_project,
            "post_tool_use.py",
            {"tool_name": "Bash", "tool_response": raw_output},
        )
        hook_times.append(elapsed)
    visible = post_tool.get("reason", "")
    archived_line = next(
        (line for line in visible.splitlines() if line.startswith("full_output: ")),
        "",
    )
    archived_path = Path(archived_line.removeprefix("full_output: "))
    if not archived_path.is_absolute():
        archived_path = failing_project / archived_path
    archived = archived_path.read_text(encoding="utf-8")
    raw_hash = hashlib.sha256(raw_output.encode()).hexdigest()
    archived_hash = hashlib.sha256(archived.encode()).hexdigest()
    raw_tokens = token_count(raw_output)
    visible_tokens = token_count(visible)
    automatic = {
        "session_start": session == {},
        "user_prompt_submit": bool(
            prompt.get("hookSpecificOutput", {}).get("additionalContext")
        ),
        "pre_tool_use": "/scripts/contextguard" in json.dumps(pre_tool),
        "post_tool_use": post_tool.get("decision") == "block",
    }
    equivalence = {
        "raw_exit_code": test_proc.returncode,
        "archived_raw_matches": raw_hash == archived_hash,
        "raw_sha256": raw_hash,
        "archived_sha256": archived_hash,
        "summary_and_failed_tests_preserved": (
            "130 failed" in visible
            and "failed_tests:" in visible
            and "tests/test_hard_output.py::test_hard_failure_matrix" in visible
        ),
    }
    tokens = {
        "tokenizer": "o200k_base via tiktoken" if TOKENIZER else "estimated at four UTF-8 bytes per token",
        "raw_visible": raw_tokens,
        "contextguard_visible": visible_tokens,
        "saved": raw_tokens - visible_tokens,
        "reduction_percent": round((raw_tokens - visible_tokens) / raw_tokens * 100, 2),
        "hook_seconds_median": round(statistics.median(hook_times), 6),
        "timing_samples": timing_samples,
    }
    return automatic, equivalence, tokens


def evaluate_execution_protection(plugin: Path, root: Path) -> tuple[dict, dict]:
    project = root / "runner-project"
    project.mkdir()
    script = project / "emit_failures.py"
    script.write_text(
        "for index in range(130):\n"
        "    print(f'FAILED tests/test_hard_output.py::test_case_{index} - AssertionError: deterministic failure {index}')\n"
        "print('130 failed in 0.50s')\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    initialized = run_cli(plugin, project, "init")
    if initialized.returncode != 0:
        raise RuntimeError(initialized.stdout + initialized.stderr)
    command = [sys.executable, str(script)]
    raw = subprocess.run(command, cwd=project, text=True, capture_output=True)
    raw_output = raw.stdout + raw.stderr
    runner = project / ".contextguard" / "bin" / "contextguard"
    protected = subprocess.run(
        [str(runner), "capture", "--", *command],
        cwd=project,
        text=True,
        capture_output=True,
    )
    summaries = sorted((project / ".contextguard" / "tmp").glob("command-*.summary.json"))
    summary = json.loads(summaries[-1].read_text(encoding="utf-8"))
    archived = Path(summary["stdout_path"]).read_text(encoding="utf-8") + Path(
        summary["stderr_path"]
    ).read_text(encoding="utf-8")
    raw_tokens = token_count(raw_output)
    visible_tokens = token_count(protected.stdout + protected.stderr)
    execution = {
        "runner_exists": runner.is_file(),
        "runner_executable": bool(runner.stat().st_mode & 0o111),
        "runner_used": "ContextGuard capture summary" in protected.stdout,
        "exit_code_preserved": protected.returncode == raw.returncode,
        "archived_raw_matches": hashlib.sha256(archived.encode()).hexdigest()
        == hashlib.sha256(raw_output.encode()).hexdigest(),
        "visible_output_reduced": visible_tokens < raw_tokens,
        "raw_visible_tokens": raw_tokens,
        "protected_visible_tokens": visible_tokens,
        "reduction_percent": round((raw_tokens - visible_tokens) / raw_tokens * 100, 2),
    }
    tokens = {
        "tokenizer": "o200k_base via tiktoken" if TOKENIZER else "estimated at four UTF-8 bytes per token",
        "raw_visible": raw_tokens,
        "contextguard_visible": visible_tokens,
        "saved": raw_tokens - visible_tokens,
        "reduction_percent": execution["reduction_percent"],
        "measurement": "project-local capture stdout observed by the host",
    }
    return execution, tokens


def run_acceptance(output: Path, timing_samples: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="contextguard-install-acceptance-") as tmp:
        root = Path(tmp)
        installed = install_plugin(root / "installed-contextguard")
        empty, existing, existing_path = initialize_projects(installed, root)
        automatic, equivalence, hook_tokens = evaluate_hooks(installed, existing_path, timing_samples)
        execution, tokens = evaluate_execution_protection(installed, root)
        package = {
            "installed_copy_used": installed != SOURCE_PLUGIN,
            "manifest_matches": file_sha256(installed / ".codex-plugin/plugin.json")
            == file_sha256(SOURCE_PLUGIN / ".codex-plugin/plugin.json"),
            "hooks_match": file_sha256(installed / "hooks/hooks.json")
            == file_sha256(SOURCE_PLUGIN / "hooks/hooks.json"),
        }
        accepted = all(
            [
                *package.values(),
                empty["initialized"],
                empty["automatic_init"],
                empty["project_kind"] == "empty",
                empty["index_exists"],
                existing["initialized"],
                existing["automatic_init"],
                existing["project_kind"] == "existing",
                existing["user_content_preserved"],
                existing["managed_section_added"],
                *execution.values(),
                *automatic.values(),
                equivalence["archived_raw_matches"],
                equivalence["summary_and_failed_tests_preserved"],
                tokens["saved"] > 0,
                tokens["reduction_percent"] > 0,
            ]
        )
        result = {
            "benchmark": "isolated-plugin-install-acceptance",
            "guarantee_scope": "Deterministic installed project runner and package logic; real Codex model behavior remains stochastic.",
            "accepted": accepted,
            "package": package,
            "empty_project": empty,
            "existing_project": existing,
            "execution_protection": execution,
            "automatic_hooks": automatic,
            "output_equivalence": equivalence,
            "tokens": tokens,
            "hook_output_tokens": hook_tokens,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=SOURCE_PLUGIN / "benchmarks/results/install-acceptance-2026-06-12.json",
    )
    parser.add_argument("--timing-samples", type=int, default=7)
    args = parser.parse_args(argv)
    result = run_acceptance(args.output, args.timing_samples)
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())
