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
    assert "additionalContext" not in output


def test_allowed_pre_tool_advice_is_recorded_but_not_injected(tmp_path: Path):
    run_hook("session_start.py", {}, tmp_path)
    result = run_hook(
        "pre_tool_use.py",
        {"tool_name": "Bash", "tool_input": {"command": "pytest -q"}},
        tmp_path,
    )
    assert "additionalContext" not in result["hookSpecificOutput"]


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


def test_session_start_initialized_injects_session_gate(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    result = run_hook("session_start.py", {}, tmp_path)
    context = result.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "session gate" in context.lower()
    assert "capture" in context


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
    assert result == {}
    assert list((tmp_path / ".contextguard" / "tmp").glob("tool-output-*.txt"))
    metrics = tmp_path / ".contextguard" / "tmp" / "hook-output-metrics.jsonl"
    record = json.loads(metrics.read_text().splitlines()[-1])
    assert record["raw_bytes"] > 0
    assert record["model_visible_bytes"] == 0


def test_post_tool_use_compacts_noisy_medium_output(tmp_path: Path):
    payload = {"tool_name": "Bash", "tool_response": "FAILED test_case file.py:12 error\n" * 80}
    result = run_hook("post_tool_use.py", payload, tmp_path)
    assert result == {}


def test_post_tool_use_keeps_failed_test_names_visible(tmp_path: Path):
    output = "\n".join(
        ["FAILED tests/test_orders.py::test_cap - AssertionError: cap"]
        + [f"FAILED tests/test_orders.py::test_case_{index} - AssertionError" for index in range(40)]
        + ["41 failed in 0.25s"]
    )
    result = run_hook("post_tool_use.py", {"tool_name": "Bash", "tool_response": output}, tmp_path)
    assert result == {}
    summaries = list((tmp_path / ".contextguard" / "tmp").glob("tool-output-*.summary.json"))
    archived = json.loads(summaries[-1].read_text())
    assert "tests/test_orders.py::test_cap" in archived["failed_tests"]


def test_post_tool_use_references_repeated_large_evidence(tmp_path: Path):
    payload = {"tool_name": "Bash", "tool_response": "ERROR stable hook failure\n" * 5000}

    assert run_hook("post_tool_use.py", payload, tmp_path) == {}
    assert run_hook("post_tool_use.py", payload, tmp_path) == {}
    summaries = sorted((tmp_path / ".contextguard" / "tmp").glob("tool-output-*.summary.json"))
    repeated = json.loads(summaries[-1].read_text())["repeated_evidence"]
    assert repeated["repeated"] is True
    assert repeated["occurrences"] == 2


def test_pre_compact_persists_compact_session_facts(tmp_path: Path):
    result = run_hook(
        "pre_compact.py",
        {"current_objective": "finish policy", "changed_files": ["a.py"], "transcript": "x" * 10000},
        tmp_path,
    )
    assert result["hookSpecificOutput"]["hookEventName"] == "PreCompact"
    assert "ContextGuard resume capsule:" in result["hookSpecificOutput"]["additionalContext"]
    capsule = (tmp_path / ".contextguard" / "sessions" / "latest.json").read_text()
    assert "finish policy" in capsule
    assert "transcript" not in capsule
    checkpoint = json.loads(capsule)
    assert checkpoint["version"] == 2
    assert checkpoint["checkpoint_id"]


def test_pre_compact_emits_bounded_resume_capsule(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}", encoding="utf-8")

    result = run_hook(
        "pre_compact.py",
        {
            "current_objective": "finish compaction",
            "likely_relevant_files": ["contextguard/contextguard/context_capsule.py"],
            "likely_relevant_symbols": ["build_session_capsule@contextguard/contextguard/context_capsule.py:46"],
            "changed_files": ["contextguard/contextguard/session_state.py"],
            "verified_tests": ["test_session_state.py::test_checkpoint_persistence_merges_sparse_updates"],
            "known_failures": ["none"],
            "active_constraints": ["keep the resume capsule bounded"],
            "next_action": "run focused tests",
            "transcript": "x" * 10000,
        },
        tmp_path,
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    assert "ContextGuard resume capsule:" in context
    assert "current_objective=finish compaction" in context
    assert "changed_files=contextguard/contextguard/session_state.py" in context
    assert "verified_tests=test_session_state.py::test_checkpoint_persistence_merges_sparse_updates" in context
    assert "next_action=run focused tests" in context
    assert "transcript" not in context


def test_pre_tool_use_rewrites_repeated_unchanged_read_without_blocking(tmp_path: Path):
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
    assert "snapshot app.py" in output["updatedInput"]["command"]


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
    assert result == {}


def test_user_prompt_does_not_repeat_session_start_resume_context(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    from contextguard.context_capsule import persist_session_capsule

    persist_session_capsule(tmp_path, {"current_objective": "old objective", "next_action": "old next action"})

    result = run_hook("user_prompt_submit.py", {"prompt": "fix billing"}, tmp_path)
    context = result.get("hookSpecificOutput", {}).get("additionalContext", "")

    assert "old objective" not in context
    assert "old next action" not in context


def test_user_prompt_injects_ticket_evidence_once_without_replay(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    (tmp_path / "SUPPORT_TICKET.md").write_text(
        "Customer reports inventory retry failure.\n",
        encoding="utf-8",
    )

    result = run_hook(
        "user_prompt_submit.py",
        {"prompt": "Investigate inventory retry failure in SUPPORT_TICKET.md"},
        tmp_path,
    )
    context = result.get("hookSpecificOutput", {}).get("additionalContext", "")

    assert "ContextGuard task working set" in context
    assert "SUPPORT_TICKET.md sha=" in context

    repeated = run_hook(
        "user_prompt_submit.py",
        {"prompt": "Investigate inventory retry failure in SUPPORT_TICKET.md"},
        tmp_path,
    )
    assert repeated == {}


def test_user_prompt_injects_task_evidence_once_for_bounded_feature(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    (tmp_path / "parser.py").write_text("def parse(value): return value\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_parser.py").write_text("def test_parse(): pass\n")

    result = run_hook(
        "user_prompt_submit.py",
        {"prompt": "Implement the validated parser change in parser.py and add focused parser tests."},
        tmp_path,
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    assert "ContextGuard task working set" in context
    assert "parser.py sha=" in context
    assert "delegate exactly one" not in context
    assert "contextguard-worker" not in context

    repeated = run_hook(
        "user_prompt_submit.py",
        {"prompt": "Implement the validated parser change in parser.py and add focused parser tests."},
        tmp_path,
    )
    assert repeated == {}


def test_user_prompt_does_not_route_security_migration(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    (tmp_path / "auth.py").write_text("SCHEMA = 1\n")

    result = run_hook(
        "user_prompt_submit.py",
        {"prompt": "Migrate the production authentication schema in auth.py without data loss."},
        tmp_path,
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    assert "contextguard-worker" not in context


def test_subagent_start_denies_worker_when_routing_locked(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    reset_session_state(tmp_path)
    session = load_session_state(tmp_path)
    session["routing_locked"] = True
    session["routing_lock_reasons"] = ["migration"]
    save_session_state(tmp_path, session)

    result = run_hook(
        "subagent_start.py",
        {"agent_type": "contextguard-worker", "model": "gpt-5.4-mini", "thread_id": "worker-1"},
        tmp_path,
    )

    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "routing lock" in output["permissionDecisionReason"].lower()
    assert "Do not spawn any subagent" in output["additionalContext"]


def test_pre_compact_injects_archive_context_when_captures_exist(tmp_path: Path):
    from contextguard.history_pack import record_archive_metadata

    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    record_archive_metadata(
        tmp_path,
        archive_path="/tmp/summary.json",
        fingerprint="fp-1",
        raw_bytes=4000,
    )

    result = run_hook(
        "pre_compact.py",
        {"current_objective": "finish policy", "changed_files": ["a.py"]},
        tmp_path,
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    assert "archive index" in context
    assert "1 captures" in context


def test_subagent_hooks_record_actual_routing_lifecycle(tmp_path: Path):
    state = tmp_path / ".contextguard"
    state.mkdir()
    (state / "manifest.json").write_text("{}")
    reset_session_state(tmp_path)

    started = run_hook(
        "subagent_start.py",
        {"agent_type": "contextguard-worker", "model": "gpt-5.4-mini", "thread_id": "worker-1"},
        tmp_path,
    )
    stopped = run_hook(
        "subagent_stop.py",
        {"agent_type": "contextguard-worker", "model": "gpt-5.4-mini", "thread_id": "worker-1", "status": "completed"},
        tmp_path,
    )

    assert "bounded package" in started["hookSpecificOutput"]["additionalContext"]
    assert stopped == {}
    session = load_session_state(tmp_path)
    assert session["routing_events"] == [
        {"event": "start", "agent_type": "contextguard-worker", "model": "gpt-5.4-mini", "thread_id": "worker-1"},
        {"event": "stop", "agent_type": "contextguard-worker", "model": "gpt-5.4-mini", "thread_id": "worker-1", "status": "completed"},
    ]
    assert session["metrics"]["routed_workers_started"] == 1
    assert session["metrics"]["routed_workers_completed"] == 1
