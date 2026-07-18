#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PLUGIN_ROOT.parent
PROMPT = """Implement the settlement reconciliation feature described in SPEC.md.

Requirements:
- before editing, run `python3 -m pytest -q` exactly once and follow the repository instructions for safe command execution
- preserve the public API and existing behavior
- use Decimal-safe HALF_EVEN currency conversion
- reject duplicate event IDs idempotently
- apply per-account caps before the global settlement cap
- produce a balanced ledger with fee posting
- keep audit records deterministic and stably ordered
- make the CLI emit the canonical JSON result
- run the complete test suite and fix all failures

Do not weaken, delete, or skip tests. Work directly in the repository and finish only when validation passes.
"""


INITIAL_FILES = {
    "pyproject.toml": """[build-system]\nrequires = [\"setuptools>=68\"]\nbuild-backend = \"setuptools.build_meta\"\n\n[project]\nname = \"hard-settlement\"\nversion = \"0.1.0\"\nrequires-python = \">=3.9\"\n\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\npythonpath = [\".\"]\n""",
    "SPEC.md": """# Settlement Reconciliation

`settlement.service.reconcile(payload)` must return a JSON-serializable dictionary.

1. Parse monetary values with `Decimal`; convert currencies to USD cents using rates in the payload and `ROUND_HALF_EVEN`.
2. Ignore later occurrences of a duplicate `event_id` and report those IDs in `duplicates`.
3. Sort accepted events by descending priority, then ascending `event_id`.
4. Apply each account's USD-cent cap before the global cap. Events may be partially accepted.
5. The processing fee is deducted after allocation. The fee cannot exceed the allocated amount.
6. Emit a balanced ledger: debit `settlement_receivable` for allocated cents, credit `merchant_cash` for posted cents, and credit `processing_fees` for the fee.
7. Audit rows contain `event_id`, `account`, `requested_minor`, `accepted_minor`, `status`; order must match allocation order.
8. Return keys: `settlement_id`, `allocated_minor`, `fee_minor`, `posted_minor`, `duplicates`, `ledger`, `audit`.
9. `python -m settlement.cli scenario.json` prints the result as sorted JSON.
""",
    "settlement/__init__.py": "from .service import reconcile\n\n__all__ = [\"reconcile\"]\n",
    "settlement/money.py": """from decimal import Decimal\n\n\ndef to_usd_minor(amount: str, currency: str, rates: dict) -> int:\n    # BUG: float conversion and truncation are not accounting safe.\n    return int(float(amount) * float(rates[currency]) * 100)\n""",
    "settlement/allocation.py": """def allocate(events, account_caps, global_cap):\n    # BUG: caps, priority, duplicates, and partial acceptance are ignored.\n    return [(event, event[\"requested_minor\"]) for event in events]\n""",
    "settlement/ledger.py": """def build_ledger(allocated_minor: int, fee_minor: int):\n    # BUG: fee entry and balancing information are missing.\n    return [{\"account\": \"merchant_cash\", \"credit_minor\": allocated_minor}]\n""",
    "settlement/service.py": """from .allocation import allocate\nfrom .ledger import build_ledger\nfrom .money import to_usd_minor\n\n\ndef reconcile(payload: dict) -> dict:\n    events = []\n    for item in payload[\"events\"]:\n        event = dict(item)\n        event[\"requested_minor\"] = to_usd_minor(item[\"amount\"], item[\"currency\"], payload[\"rates\"])\n        events.append(event)\n    allocations = allocate(events, payload[\"account_caps_minor\"], payload[\"global_cap_minor\"])\n    allocated = sum(value for _, value in allocations)\n    fee = int(payload[\"fee_minor\"])\n    return {\n        \"settlement_id\": payload[\"settlement_id\"],\n        \"allocated_minor\": allocated,\n        \"fee_minor\": fee,\n        \"posted_minor\": allocated - fee,\n        \"duplicates\": [],\n        \"ledger\": build_ledger(allocated, fee),\n        \"audit\": [],\n    }\n""",
    "settlement/cli.py": """import json\nimport sys\nfrom pathlib import Path\n\nfrom .service import reconcile\n\n\ndef main():\n    payload = json.loads(Path(sys.argv[1]).read_text())\n    print(json.dumps(reconcile(payload), sort_keys=True))\n\n\nif __name__ == \"__main__\":\n    main()\n""",
    "scenario.json": json.dumps(
        {
            "settlement_id": "stl-001",
            "rates": {"USD": "1", "EUR": "1.10", "GBP": "1.25"},
            "account_caps_minor": {"alpha": 5200, "beta": 4300},
            "global_cap_minor": 9424,
            "fee_minor": 250,
            "events": [
                {"event_id": "evt-003", "account": "alpha", "amount": "25.005", "currency": "USD", "priority": 2},
                {"event_id": "evt-001", "account": "alpha", "amount": "40.00", "currency": "EUR", "priority": 3},
                {"event_id": "evt-002", "account": "beta", "amount": "50.00", "currency": "GBP", "priority": 1},
                {"event_id": "evt-001", "account": "alpha", "amount": "999.00", "currency": "USD", "priority": 9},
            ],
        },
        indent=2,
    )
    + "\n",
}


REFERENCE_FILES = {
    "settlement/money.py": """from decimal import Decimal, ROUND_HALF_EVEN\n\n\ndef to_usd_minor(amount: str, currency: str, rates: dict) -> int:\n    value = Decimal(str(amount)) * Decimal(str(rates[currency])) * Decimal(100)\n    return int(value.quantize(Decimal(\"1\"), rounding=ROUND_HALF_EVEN))\n""",
    "settlement/allocation.py": """def allocate(events, account_caps, global_cap):\n    remaining_accounts = {key: int(value) for key, value in account_caps.items()}\n    remaining_global = int(global_cap)\n    allocations = []\n    for event in sorted(events, key=lambda item: (-int(item.get(\"priority\", 0)), item[\"event_id\"])):\n        account = event[\"account\"]\n        requested = int(event[\"requested_minor\"])\n        accepted = max(0, min(requested, remaining_accounts.get(account, 0), remaining_global))\n        remaining_accounts[account] = max(0, remaining_accounts.get(account, 0) - accepted)\n        remaining_global -= accepted\n        allocations.append((event, accepted))\n    return allocations\n""",
    "settlement/ledger.py": """def build_ledger(allocated_minor: int, fee_minor: int):\n    posted = allocated_minor - fee_minor\n    return [\n        {\"account\": \"settlement_receivable\", \"debit_minor\": allocated_minor, \"credit_minor\": 0},\n        {\"account\": \"merchant_cash\", \"debit_minor\": 0, \"credit_minor\": posted},\n        {\"account\": \"processing_fees\", \"debit_minor\": 0, \"credit_minor\": fee_minor},\n    ]\n""",
    "settlement/service.py": """from .allocation import allocate\nfrom .ledger import build_ledger\nfrom .money import to_usd_minor\n\n\ndef reconcile(payload: dict) -> dict:\n    events = []\n    duplicates = []\n    seen = set()\n    for item in payload[\"events\"]:\n        event_id = item[\"event_id\"]\n        if event_id in seen:\n            if event_id not in duplicates:\n                duplicates.append(event_id)\n            continue\n        seen.add(event_id)\n        event = dict(item)\n        event[\"requested_minor\"] = to_usd_minor(item[\"amount\"], item[\"currency\"], payload[\"rates\"])\n        events.append(event)\n    allocations = allocate(events, payload[\"account_caps_minor\"], payload[\"global_cap_minor\"])\n    allocated = sum(value for _, value in allocations)\n    fee = min(int(payload[\"fee_minor\"]), allocated)\n    audit = []\n    for event, accepted in allocations:\n        requested = event[\"requested_minor\"]\n        status = \"accepted\" if accepted == requested else \"partial\" if accepted else \"rejected\"\n        audit.append({\n            \"event_id\": event[\"event_id\"],\n            \"account\": event[\"account\"],\n            \"requested_minor\": requested,\n            \"accepted_minor\": accepted,\n            \"status\": status,\n        })\n    return {\n        \"settlement_id\": payload[\"settlement_id\"],\n        \"allocated_minor\": allocated,\n        \"fee_minor\": fee,\n        \"posted_minor\": allocated - fee,\n        \"duplicates\": duplicates,\n        \"ledger\": build_ledger(allocated, fee),\n        \"audit\": audit,\n    }\n""",
}


TEST_FILE = r'''import json
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import pytest

from settlement.money import to_usd_minor
from settlement.service import reconcile


def scenario():
    return json.loads((Path(__file__).parents[1] / "scenario.json").read_text())


@pytest.mark.parametrize("index", range(64))
def test_half_even_conversion_matrix(index):
    whole = index % 17
    amount = f"{whole}.{index % 10}05"
    expected = int((Decimal(amount) * Decimal("1.10") * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
    assert to_usd_minor(amount, "EUR", {"EUR": "1.10"}) == expected


@pytest.mark.parametrize("global_cap", range(9000, 9064))
def test_caps_balance_and_idempotency_matrix(global_cap):
    payload = scenario()
    payload["global_cap_minor"] = global_cap
    result = reconcile(payload)
    assert result["allocated_minor"] <= global_cap
    assert result["duplicates"] == ["evt-001"]
    assert sum(row.get("debit_minor", 0) for row in result["ledger"]) == sum(row.get("credit_minor", 0) for row in result["ledger"])
    assert [row["event_id"] for row in result["audit"]] == ["evt-001", "evt-003", "evt-002"]


def test_canonical_scenario():
    result = reconcile(scenario())
    assert result["settlement_id"] == "stl-001"
    assert result["allocated_minor"] == 9424
    assert result["fee_minor"] == 250
    assert result["posted_minor"] == 9174
    assert result["duplicates"] == ["evt-001"]
    assert result["audit"][0]["accepted_minor"] == 4400
    assert result["audit"][1]["accepted_minor"] == 800
    assert result["audit"][2]["accepted_minor"] == 4224


def test_duplicate_reporting_is_idempotent_for_three_occurrences():
    payload = scenario()
    payload["events"].append(dict(payload["events"][0], event_id="evt-001"))
    result = reconcile(payload)
    assert result["duplicates"] == ["evt-001"]
'''


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative, text in INITIAL_FILES.items():
        _write(root / relative, text)
    _write(root / "tests/test_settlement.py", TEST_FILE)
    noise = root / "data"
    noise.mkdir()
    _write(noise / "historic-settlements.log", "\n".join(f"ERROR legacy settlement {index} mismatch account={index % 97}" for index in range(30000)))
    _write(noise / "archive.jsonl", "\n".join(json.dumps({"id": index, "amount": index % 1000, "status": "closed"}) for index in range(20000)))
    _write(root / ".gitignore", ".contextguard/\n__pycache__/\n.pytest_cache/\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "ContextGuard Benchmark"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial hard settlement fixture"], cwd=root, check=True)
    return root


def apply_reference_solution(root: Path) -> None:
    for relative, text in REFERENCE_FILES.items():
        _write(root / relative, text)


def validate_fixture(root: Path) -> dict:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, text=True, capture_output=True)
    output = proc.stdout + proc.stderr
    match = re.search(r"(\d+) passed", output)
    failed = re.search(r"(\d+) failed", output)
    canonical_proc = subprocess.run(
        [sys.executable, "-m", "settlement.cli", "scenario.json"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    try:
        canonical = json.loads(canonical_proc.stdout) if canonical_proc.returncode == 0 else {}
    except json.JSONDecodeError:
        canonical = {}
    collected = 130
    return {
        "exit_code": proc.returncode,
        "passed_tests": int(match.group(1)) if match else 0,
        "failed_tests": int(failed.group(1)) if failed else (0 if proc.returncode == 0 else 1),
        "collected_tests": collected,
        "output": output,
        "canonical_exit_code": canonical_proc.returncode,
        "canonical_output": canonical,
    }


def parse_codex_jsonl(text: str) -> dict:
    usage = {}
    turn_completed_events = 0
    tool_output_bytes = 0
    command_executions = 0
    file_changes = 0
    final_response = ""
    commands = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed":
            turn_completed_events += 1
            usage = event.get("usage") or usage
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        item_type = item.get("type")
        if item_type == "command_execution":
            command_executions += 1
            commands.append(item.get("command") or "")
            output = item.get("aggregated_output") or item.get("output") or ""
            tool_output_bytes += len(str(output).encode())
        elif item_type == "file_change":
            file_changes += 1
        elif item_type == "agent_message":
            final_response = item.get("text") or final_response
    input_tokens = int(usage.get("input_tokens", 0))
    cached_tokens = int(usage.get("cached_input_tokens", 0))
    return {
        "usage_event_seen": turn_completed_events > 0,
        "turn_completed_events": turn_completed_events,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "uncached_input_tokens": max(0, input_tokens - cached_tokens),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "reasoning_output_tokens": int(usage.get("reasoning_output_tokens", 0)),
        "tool_output_bytes": tool_output_bytes,
        "command_executions": command_executions,
        "file_changes": file_changes,
        "final_response": final_response,
        "final_response_bytes": len(final_response.encode()),
        "commands": commands,
    }


def build_codex_command(project: Path, *, optimized: bool) -> list[str]:
    command = shlex.split(os.environ.get("CONTEXTGUARD_CODEX_COMMAND", "codex"))
    command.extend([
        "exec", "--json", "--ephemeral", "--ignore-rules",
        "--model", "gpt-5.5", "-c", 'model_reasoning_effort="medium"',
        "--sandbox", "danger-full-access", "-c", 'approval_policy="never"', "-c", "features.plugins=false",
    ])
    command.extend(["-C", str(project), PROMPT])
    return command


def prepare_codex_home(home: Path, project: Path, *, optimized: bool = False) -> None:
    home.mkdir(parents=True, exist_ok=True)
    auth = Path.home() / ".codex" / "auth.json"
    if not auth.exists():
        raise RuntimeError("Codex authentication is unavailable at ~/.codex/auth.json")
    shutil.copy2(auth, home / "auth.json")
    os.chmod(home / "auth.json", 0o600)
    canonical_project = Path(os.path.realpath(project))
    config = f'[projects."{canonical_project.as_posix()}"]\ntrust_level = "trusted"\n'
    (home / "config.toml").write_text(config, encoding="utf-8")


def prepare_optimized_project(project: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PLUGIN_ROOT)
    subprocess.run(
        [sys.executable, "-m", "contextguard.cli", "init", "--path", str(project)],
        cwd=PLUGIN_ROOT,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )


def run_trial(project: Path, codex_home: Path, artifact_dir: Path, *, optimized: bool, timeout: int) -> dict:
    prepare_codex_home(codex_home, project, optimized=optimized)
    if optimized:
        prepare_optimized_project(project)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(codex_home)
    started = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            build_codex_command(project, optimized=optimized),
            cwd=project,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        exit_code = 124
    elapsed = time.perf_counter() - started
    parsed = parse_codex_jsonl(stdout)
    parsed["exact_baseline_command"] = any(
        command.endswith("'python3 -m pytest -q'") or command == "python3 -m pytest -q"
        for command in parsed["commands"]
    )
    parsed["capture_runner_used"] = any(
        ".contextguard/bin/contextguard" in command
        and "capture" in command
        and "python3 -m pytest -q" in command
        for command in parsed["commands"]
    )
    parsed["raw_tool_output_bytes"] = parsed["tool_output_bytes"]
    parsed["model_visible_tool_output_bytes"] = parsed["tool_output_bytes"]
    validation = validate_fixture(project)
    diff = subprocess.run(["git", "diff", "--", ".", ":(exclude).codex", ":(exclude)AGENTS.md", ":(exclude)docs"], cwd=project, text=True, capture_output=True).stdout
    (artifact_dir / "events.jsonl").write_text(stdout, encoding="utf-8")
    (artifact_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    (artifact_dir / "final-response.txt").write_text(parsed["final_response"], encoding="utf-8")
    (artifact_dir / "diff.patch").write_text(diff, encoding="utf-8")
    (artifact_dir / "validation.txt").write_text(validation["output"], encoding="utf-8")
    return {
        "optimized": optimized,
        "codex_exit_code": exit_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 3),
        **parsed,
        "validation": {key: value for key, value in validation.items() if key != "output"},
        "repository_hash": repository_hash(project),
        "diff_bytes": len(diff.encode()),
        "stderr_bytes": len(stderr.encode()),
    }


def percent_change(raw: int | float, optimized: int | float) -> float | None:
    if not raw:
        return None
    return round(((optimized - raw) / raw) * 100, 2)


def execute_real_ab(output_dir: Path, *, timeout: int = 1200) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="contextguard-real-codex-ab-") as tmp:
        root = Path(tmp)
        raw_project = create_fixture(root / "raw-project")
        optimized_project = create_fixture(root / "optimized-project")
        raw = run_trial(raw_project, root / "raw-home", output_dir / "raw", optimized=False, timeout=timeout)
        optimized = run_trial(optimized_project, root / "optimized-home", output_dir / "contextguard", optimized=True, timeout=timeout)
        equivalent = (
            raw["validation"]["exit_code"] == 0
            and optimized["validation"]["exit_code"] == 0
            and raw["validation"]["canonical_output"] == optimized["validation"]["canonical_output"]
            and raw["validation"]["passed_tests"] == optimized["validation"]["passed_tests"]
            and raw["exact_baseline_command"]
            and optimized["capture_runner_used"]
        )
        comparison = {}
        for key in (
            "input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens",
            "reasoning_output_tokens", "tool_output_bytes", "elapsed_seconds", "command_executions",
            "raw_tool_output_bytes", "model_visible_tool_output_bytes", "file_changes",
            "final_response_bytes", "diff_bytes",
            "capture_runner_used",
        ):
            comparison[key] = {
                "raw": raw[key],
                "contextguard": optimized[key],
                "change_percent": percent_change(raw[key], optimized[key]),
            }
        result = {
            "benchmark": "real-codex-hard-settlement-ab",
            "model": "gpt-5.5",
            "reasoning_effort": "medium",
            "codex_cli": subprocess.run(
                [*shlex.split(os.environ.get("CONTEXTGUARD_CODEX_COMMAND", "codex")), "--version"],
                text=True,
                capture_output=True,
            ).stdout.strip(),
            "same_prompt": True,
            "equivalent_result": equivalent,
            "raw": raw,
            "contextguard": optimized,
            "comparison": comparison,
            "limitations": [
                "Single controlled sample; model execution is stochastic.",
                "The installed Codex CLI may include fixed system context not controlled by this harness.",
                "Cached input tokens are reported separately from uncached input tokens.",
            ],
        }
        (output_dir / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result


def repository_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or ".contextguard" in path.parts or ".codex" in path.parts:
            continue
        if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=PLUGIN_ROOT / "benchmarks" / "results" / "real-codex-hard-ab-2026-06-10")
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args(argv)
    if args.self_check:
        with tempfile.TemporaryDirectory(prefix="contextguard-real-ab-") as tmp:
            fixture = create_fixture(Path(tmp) / "fixture")
            before = validate_fixture(fixture)
            apply_reference_solution(fixture)
            after = validate_fixture(fixture)
            print(json.dumps({"before": before["exit_code"], "after": after["exit_code"], "tests": after["passed_tests"]}))
            return int(after["exit_code"] != 0)
    if args.run:
        result = execute_real_ab(args.output_dir, timeout=args.timeout)
        print(json.dumps(result["comparison"], indent=2, sort_keys=True))
        return int(not result["equivalent_result"])
    parser.error("choose --self-check or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
