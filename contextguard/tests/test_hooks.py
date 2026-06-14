import json
import subprocess
import sys
from pathlib import Path

from contextguard.optimization_advisor import record_command
from contextguard.session_state import load_session_state, reset_session_state, save_session_state


ROOT = Path(__file__).resolve().parents[1]


def run_hook(name: str, payload: dict, cwd: Path):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "hooks" / name)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=cwd,
        check=True,
    )
    return json.loads(proc.stdout)


def test_cached_hook_commands_fail_open_after_plugin_cache_is_removed(tmp_path: Path):
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    removed_plugin_root = tmp_path / "removed-plugin-version"

    for event_groups in hooks.values():
        for event_group in event_groups:
            for hook in event_group["hooks"]:
                proc = subprocess.run(
                    hook["command"],
                    shell=True,
                    cwd=tmp_path,
                    env={"PLUGIN_ROOT": str(removed_plugin_root)},
                    input="{}",
                    text=True,
                    capture_output=True,
                )

                assert proc.returncode == 0, hook["command"]
                assert proc.stdout == ""
                assert proc.stderr == ""


def test_hook_json_input_output(tmp_path: Path):
    result = run_hook("pre_tool_use.py", {"tool_name": "Bash", "tool_input": {"command": "cat big.log"}}, tmp_path)
    output = result["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "allow"
    assert "/scripts/contextguard" in output["updatedInput"]["command"]


def test_python_module_pytest_pipeline_is_rewritten(tmp_path: Path):
    result = run_hook(
        "pre_tool_use.py",
        {"tool_name": "Bash", "tool_input": {"command": "python3 -m pytest -q 2>&1 | tee /tmp/tests.log"}},
        tmp_path,
    )
    command = result["hookSpecificOutput"]["updatedInput"]["command"]
    assert "/scripts/contextguard" in command
    assert "python3 -m pytest" in command


def test_large_sed_log_inspection_is_rewritten(tmp_path: Path):
    result = run_hook(
        "pre_tool_use.py",
        {"tool_name": "Bash", "tool_input": {"command": "sed -n '1,260p' artifacts/CI_FAILURE.log"}},
        tmp_path,
    )
    command = result["hookSpecificOutput"]["updatedInput"]["command"]
    assert "/scripts/contextguard" in command
    assert "CI_FAILURE.log" in command


def test_stop_hook_loop_prevention(tmp_path: Path):
    result = run_hook("stop.py", {"stop_hook_active": True}, tmp_path)
    assert result == {}


def test_session_start_automatically_initializes_empty_project(tmp_path: Path):
    result = run_hook("session_start.py", {}, tmp_path)

    assert "initialized automatically" in result["hookSpecificOutput"]["additionalContext"]
    assert (tmp_path / ".contextguard" / "manifest.json").exists()
    assert (tmp_path / ".contextguard" / "tmp" / "hook-heartbeats.jsonl").exists()


def test_session_start_preserves_existing_project_content(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# User instructions\n\nNever remove this.\n")
    (tmp_path / "app.py").write_text("print('ok')\n")

    run_hook("session_start.py", {}, tmp_path)

    assert "Never remove this." in agents.read_text()
    assert "BEGIN CONTEXTGUARD MANAGED SECTION" in agents.read_text()


def test_session_start_initialized_is_silent(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    result = run_hook("session_start.py", {}, tmp_path)
    assert result == {}


def test_session_start_resets_transient_optimization_state(tmp_path: Path):
    state_dir = tmp_path / ".contextguard"
    state_dir.mkdir()
    (state_dir / "manifest.json").write_text("{}")
    reset_session_state(tmp_path)
    state = load_session_state(tmp_path)
    state["commands"] = [{"command": "rg --files", "family": "repository_listing"}]
    state["reads"] = {"key": {"hashes": {"app.py": "hash"}}}
    save_session_state(tmp_path, state)

    run_hook("session_start.py", {}, tmp_path)

    reset = load_session_state(tmp_path)
    assert reset["commands"] == []
    assert reset["reads"] == {}


def test_status_reports_session_hook_as_partial_until_tool_hook_runs(tmp_path: Path):
    run_hook("session_start.py", {}, tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "contextguard.cli", "status"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Hook status: partially observed" in proc.stdout
    assert "SessionStart" in proc.stdout

    run_hook("pre_tool_use.py", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"}}, tmp_path)
    verified = subprocess.run(
        [sys.executable, "-m", "contextguard.cli", "status"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Hook status: observed" in verified.stdout
    assert "PreToolUse" in verified.stdout


def test_status_reports_session_efficiency_metrics(tmp_path: Path):
    run_hook("session_start.py", {}, tmp_path)
    state = load_session_state(tmp_path)
    state["metrics"]["repeated_reads_detected"] = 3
    state["metrics"]["budget_advice_emitted"] = 2
    state["commands"] = [{"command": "printf ok", "family": "other"}]
    save_session_state(tmp_path, state)

    proc = subprocess.run(
        [sys.executable, "-m", "contextguard.cli", "status"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(ROOT)},
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Session commands tracked: 1" in proc.stdout
    assert "Repeated reads detected: 3" in proc.stdout
    assert "Command budget advice emitted: 2" in proc.stdout


def test_post_tool_use_stores_large_output(tmp_path: Path):
    payload = {"tool_name": "Bash", "tool_response": "ERROR repeated failure\n" * 5000}
    result = run_hook("post_tool_use.py", payload, tmp_path)
    assert result["decision"] == "block"
    assert "full_output:" in result["reason"]
    assert result["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert list((tmp_path / ".contextguard" / "tmp").glob("tool-output-*.txt"))
    metrics = tmp_path / ".contextguard" / "tmp" / "hook-output-metrics.jsonl"
    record = json.loads(metrics.read_text().splitlines()[-1])
    assert record["raw_bytes"] > record["model_visible_bytes"]


def test_post_tool_use_compacts_noisy_medium_output(tmp_path: Path):
    payload = {"tool_name": "Bash", "tool_response": "FAILED test_case file.py:12 error\n" * 80}
    result = run_hook("post_tool_use.py", payload, tmp_path)
    assert result["decision"] == "block"
    assert len(result["reason"].encode()) < 2000


def test_post_tool_use_keeps_failed_test_names_visible(tmp_path: Path):
    output = "\n".join(
        ["FAILED tests/test_orders.py::test_cap - AssertionError: cap"]
        + [f"FAILED tests/test_orders.py::test_case_{index} - AssertionError" for index in range(40)]
        + ["41 failed in 0.25s"]
    )
    result = run_hook("post_tool_use.py", {"tool_name": "Bash", "tool_response": output}, tmp_path)
    assert "failed_tests:" in result["reason"]
    assert "tests/test_orders.py::test_cap" in result["reason"]
    assert "41 failed in 0.25s" in result["reason"]


def test_post_tool_use_references_repeated_large_evidence(tmp_path: Path):
    payload = {"tool_name": "Bash", "tool_response": "ERROR stable hook failure\n" * 5000}

    first = run_hook("post_tool_use.py", payload, tmp_path)
    second = run_hook("post_tool_use.py", payload, tmp_path)

    assert "ERROR stable hook failure" in first["reason"]
    assert "ContextGuard repeated evidence" in second["reason"]
    assert "ERROR stable hook failure" not in second["reason"]
    assert len(second["reason"].encode()) < len(first["reason"].encode())


def test_pre_compact_persists_compact_session_facts(tmp_path: Path):
    result = run_hook(
        "pre_compact.py",
        {"current_objective": "finish policy", "changed_files": ["a.py"], "transcript": "x" * 10000},
        tmp_path,
    )
    assert result == {}
    capsule = (tmp_path / ".contextguard" / "sessions" / "latest.json").read_text()
    assert "finish policy" in capsule
    assert "transcript" not in capsule
    checkpoint = json.loads(capsule)
    assert checkpoint["version"] == 1
    assert checkpoint["checkpoint_id"]


def test_pre_tool_use_adds_non_blocking_repeated_read_advice(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    (tmp_path / "app.py").write_text("print('ok')\n")
    reset_session_state(tmp_path)
    record_command(tmp_path, "cat app.py", succeeded=True)

    result = run_hook(
        "pre_tool_use.py",
        {"tool_name": "Bash", "tool_input": {"command": "cat app.py"}},
        tmp_path,
    )

    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "allow"
    assert "unchanged" in output["additionalContext"].lower()
    assert "updatedInput" in output


def test_post_tool_use_records_successful_command_for_budget(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    reset_session_state(tmp_path)

    run_hook(
        "post_tool_use.py",
        {
            "tool_name": "Bash",
            "tool_input": {"command": "rg --files"},
            "tool_response": "app.py\n",
            "exit_code": 0,
        },
        tmp_path,
    )

    session = load_session_state(tmp_path)
    assert session["commands"][-1]["family"] == "repository_listing"


def test_user_prompt_context_uses_codex_hook_envelope(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    result = run_hook("user_prompt_submit.py", {"prompt": "fix billing"}, tmp_path)
    output = result["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit"
    assert "ContextGuard" in output["additionalContext"]
