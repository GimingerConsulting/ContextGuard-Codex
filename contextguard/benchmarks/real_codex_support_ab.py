#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from benchmarks.real_codex_backend_ab import (
    INITIAL_FILES,
    REFERENCE_FILES,
    _concurrency_probe,
    _json_command,
    _write,
    percent_change,
    prepare_codex_home,
    prepare_optimized_project,
    repository_hash,
    run_trial as backend_run_trial,
)


PROMPT = """Please investigate and fix the customer issue in SUPPORT_TICKET.md.

Treat this like a normal maintenance task in an unfamiliar repository:
- before editing, run `python3 -m pytest -q` exactly once and follow repository instructions for safe command execution
- reproduce the reported behavior from the ticket and available logs
- identify the root cause instead of applying a narrow data-specific workaround
- preserve existing public behavior unless the ticket shows it is broken
- add focused regression coverage for the bug
- run the complete public test suite and any useful targeted checks
- briefly document the fix in CHANGELOG.md

Do not weaken, delete, or skip tests. Work directly in the repository and finish when the issue is fixed and validation passes.
"""

RUN_ORDERS = [("raw", "contextguard"), ("contextguard", "raw"), ("raw", "contextguard")]
BENCHMARK_MODEL = os.environ.get("CONTEXTGUARD_BENCHMARK_MODEL", "gpt-5.6-sol")
REASONING_EFFORT = os.environ.get("CONTEXTGUARD_BENCHMARK_REASONING_EFFORT", "medium")
SOL_CREDITS_PER_MILLION = {"uncached_input": 125.0, "cached_input": 12.5, "output": 750.0}
API_USD_PER_MILLION = {"uncached_input": 5.0, "cached_input": 0.5, "output": 30.0}


def sol_credit_cost(run: dict) -> float:
    input_tokens = int(run.get("input_tokens", 0))
    cached = min(input_tokens, int(run.get("cached_input_tokens", 0)))
    uncached = max(0, input_tokens - cached)
    output = int(run.get("output_tokens", 0))
    credits = (
        uncached * SOL_CREDITS_PER_MILLION["uncached_input"]
        + cached * SOL_CREDITS_PER_MILLION["cached_input"]
        + output * SOL_CREDITS_PER_MILLION["output"]
    ) / 1_000_000
    return round(credits, 6)


def api_cost_usd(run: dict) -> float:
    input_tokens = int(run.get("input_tokens", 0))
    cached = min(input_tokens, int(run.get("cached_input_tokens", 0)))
    uncached = max(0, input_tokens - cached)
    output = int(run.get("output_tokens", 0))
    cost = (
        uncached * API_USD_PER_MILLION["uncached_input"]
        + cached * API_USD_PER_MILLION["cached_input"]
        + output * API_USD_PER_MILLION["output"]
    ) / 1_000_000
    return round(cost, 6)

TICKET = """# Support ticket INC-4821

**Customer:** Northstar Retail
**Severity:** High

Since last week's rollout, customers occasionally receive a successful reservation response but later see stock below zero. Retrying the same checkout request sometimes reserves the item twice. A few older warehouse records also show zero available stock after startup even though the old export contains a positive quantity.

Operations attached excerpts from production logs. The issue is easiest to observe under parallel checkout traffic. Please reproduce it, fix the underlying problem without breaking existing API clients, add regression coverage, and add a short changelog note.
"""

PUBLIC_TESTS = r'''from inventory.api import handle_request
from inventory.migration import migrate_record
from inventory.service import InventoryService


def test_legacy_api_shape_remains_available():
    service = InventoryService([{"sku": "widget", "quantity": 10}])
    result = handle_request({"sku": "widget", "quantity": 2, "request_id": "public-1"}, service)
    assert {"sku", "quantity", "remaining", "ok"} <= result.keys()


def test_migration_keeps_sku():
    assert migrate_record({"sku": "widget", "quantity": 10})["sku"] == "widget"


def test_basic_reservation_reports_success():
    service = InventoryService([{"sku": "widget", "quantity": 10}])
    assert service.reserve("widget", 2, "public-2")["ok"] is True
'''

HIDDEN_TESTS = r'''from concurrent.futures import ThreadPoolExecutor

import pytest

from inventory.migration import migrate_record
from inventory.service import InventoryService


@pytest.mark.parametrize("quantity", range(1, 65))
def test_hidden_migration_preserves_legacy_quantity(quantity):
    result = migrate_record({"sku": f"sku-{quantity}", "quantity": quantity})
    assert result["available"] == quantity


@pytest.mark.parametrize("quantity", range(1, 49))
def test_hidden_retry_is_idempotent(quantity):
    service = InventoryService([{"sku": "widget", "quantity": quantity + 5}])
    first = service.reserve("widget", quantity, f"retry-{quantity}")
    second = service.reserve("widget", quantity, f"retry-{quantity}")
    assert first == second
    assert service.records["widget"]["available"] == 5


@pytest.mark.parametrize("stock", range(1, 33))
def test_hidden_parallel_checkout_never_oversells(stock):
    service = InventoryService([{"sku": "widget", "quantity": stock}])
    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(lambda i: service.reserve("widget", 1, f"parallel-{i}"), range(stock * 2)))
    assert sum(item["ok"] for item in results) == stock
    assert service.records["widget"]["available"] == 0
    assert service.records["widget"]["reserved"] == stock
'''


def create_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    files = dict(INITIAL_FILES)
    files.pop("SPEC.md", None)
    files["SUPPORT_TICKET.md"] = TICKET
    files["CHANGELOG.md"] = "# Changelog\n\n## Unreleased\n\n"
    for relative, content in files.items():
        _write(root / relative, content)
    _write(root / "tests/test_public_behavior.py", PUBLIC_TESTS)
    _write(root / "data/production.log", "\n".join(
        f"ERROR checkout request=req-{i % 211} sku=sku-{i % 37} available={4 - (i % 9)} worker={i % 16}"
        for i in range(30000)
    ))
    _write(root / "data/warehouse-export.jsonl", "\n".join(
        json.dumps({"sku": f"sku-{i}", "quantity": i % 80 + 1, "schema_version": 1})
        for i in range(12000)
    ))
    _write(root / ".gitignore", ".contextguard/\n__pycache__/\n.pytest_cache/\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "ContextGuard Benchmark"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "legacy inventory service before incident fix"], cwd=root, check=True)
    return root


def apply_reference_solution(root: Path) -> None:
    for relative, content in REFERENCE_FILES.items():
        _write(root / relative, content)
    _write(root / "CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- Prevent duplicate and concurrent inventory reservations from overselling stock.\n")


def validate_fixture(root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="contextguard-hidden-tests-") as tmp:
        hidden = Path(tmp) / "test_hidden_acceptance.py"
        hidden.write_text(HIDDEN_TESTS, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests", str(hidden)],
            cwd=root, text=True, capture_output=True,
        )
    output = proc.stdout + proc.stderr
    passed = __import__("re").search(r"(\d+) passed", output)
    failed = __import__("re").search(r"(\d+) failed", output)
    canonical_exit, canonical = _json_command(root, "reserve", "scenario.json")
    hidden_total = 144
    total_passed = int(passed.group(1)) if passed else 0
    return {
        "exit_code": proc.returncode,
        "passed_tests": total_passed,
        "failed_tests": int(failed.group(1)) if failed else (0 if proc.returncode == 0 else 1),
        "hidden_passed_tests": hidden_total if proc.returncode == 0 else min(hidden_total, total_passed),
        "hidden_failed_tests": 0 if proc.returncode == 0 else max(1, hidden_total - min(hidden_total, total_passed)),
        "collected_tests": hidden_total + 3,
        "output": output,
        "canonical_exit_code": canonical_exit,
        "canonical_output": canonical,
        "concurrency_output": _concurrency_probe(root),
        "changelog_updated": len((root / "CHANGELOG.md").read_text().splitlines()) > 4,
    }


def build_codex_command(project: Path, *, optimized: bool) -> list[str]:
    command = shlex.split(os.environ.get("CONTEXTGUARD_CODEX_COMMAND", "codex"))
    if optimized:
        compact_limit = os.environ.get("CONTEXTGUARD_AUTO_COMPACT_TOKEN_LIMIT", "").strip()
        if compact_limit:
            command.extend([
                "-c", f"model_auto_compact_token_limit={int(compact_limit)}",
                "-c", 'model_auto_compact_token_limit_scope="total"',
            ])
        tool_limit = os.environ.get("CONTEXTGUARD_TOOL_OUTPUT_TOKEN_LIMIT", "").strip()
        if tool_limit:
            command.extend(["-c", f"tool_output_token_limit={int(tool_limit)}"])
        verbosity = os.environ.get("CONTEXTGUARD_MODEL_VERBOSITY", "").strip()
        if verbosity:
            command.extend(["-c", f'model_verbosity="{verbosity}"'])
    command.extend([
        "exec", "--json", "--ephemeral", "--ignore-rules",
        "--model", BENCHMARK_MODEL, "-c", f'model_reasoning_effort="{REASONING_EFFORT}"',
        "--sandbox", "danger-full-access", "-c", 'approval_policy="never"',
        "-c", f"features.plugins={'true' if optimized else 'false'}", "-C", str(project), PROMPT,
    ])
    return command


def prepare_optimized_project_with_hooks(target: Path) -> None:
    prepare_optimized_project(target)
    hooks = json.loads((PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
    prefix = f"PYTHONPATH={shlex.quote(str(PLUGIN_ROOT))} "
    for rules in hooks.get("hooks", {}).values():
        for rule in rules:
            for hook in rule.get("hooks", []):
                if hook.get("type") == "command" and hook.get("command"):
                    hook["command"] = prefix + str(hook["command"]).replace("$PLUGIN_ROOT", str(PLUGIN_ROOT))
    config_dir = target / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "hooks.json").write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")


def run_trial(project: Path, home: Path, artifact_dir: Path, *, optimized: bool, timeout: int) -> dict:
    import benchmarks.real_codex_backend_ab as backend

    original_prompt = backend.PROMPT
    original_validate = backend.validate_fixture
    original_command = backend.build_codex_command
    original_prepare = backend.prepare_optimized_project

    try:
        backend.PROMPT = PROMPT
        backend.validate_fixture = validate_fixture
        backend.build_codex_command = build_codex_command
        backend.prepare_optimized_project = prepare_optimized_project_with_hooks
        return backend_run_trial(project, home, artifact_dir, optimized=optimized, timeout=timeout)
    finally:
        backend.PROMPT = original_prompt
        backend.validate_fixture = original_validate
        backend.build_codex_command = original_command
        backend.prepare_optimized_project = original_prepare


def _run_one(kind: str, root: Path, artifact_dir: Path, timeout: int) -> dict:
    project = create_fixture(root / f"{kind}-project")
    return run_trial(
        project,
        root / f"{kind}-home",
        artifact_dir,
        optimized=kind == "contextguard",
        timeout=timeout,
    )


def build_release_gate(pairs: list[dict], aggregate: dict[str, dict]) -> dict[str, object]:
    pair_reductions = []
    commands_not_increased = True
    usage_complete = True
    for pair in pairs:
        raw_total = int(pair["raw"]["input_tokens"]) + int(pair["raw"]["output_tokens"])
        guarded_total = int(pair["contextguard"]["input_tokens"]) + int(pair["contextguard"]["output_tokens"])
        pair_reductions.append(round((raw_total - guarded_total) / raw_total * 100, 2) if raw_total else 0.0)
        commands_not_increased = commands_not_increased and (
            int(pair["contextguard"]["command_executions"]) <= int(pair["raw"]["command_executions"])
        )
        usage_complete = usage_complete and bool(pair["raw"].get("usage_event_seen")) and bool(
            pair["contextguard"].get("usage_event_seen")
        )
    total_change = aggregate["total_tokens"]["median_change_percent"]
    credit_change = aggregate["sol_credits"]["median_change_percent"]
    api_cost_change = aggregate["api_cost_usd"]["median_change_percent"]
    median_reduction = -float(total_change) if total_change is not None else None
    credit_reduction = -float(credit_change) if credit_change is not None else None
    api_cost_reduction = -float(api_cost_change) if api_cost_change is not None else None
    quality_passed = all(bool(pair.get("accepted")) for pair in pairs)
    passed = all(
        (
            quality_passed,
            usage_complete,
            api_cost_reduction is not None and api_cost_reduction >= 50.0,
            all(reduction > 0 for reduction in pair_reductions),
            commands_not_increased,
        )
    )
    return {
        "passed": passed,
        "quality_passed": quality_passed,
        "median_total_token_reduction_percent": round(median_reduction, 2) if median_reduction is not None else None,
        "median_sol_credit_reduction_percent": round(credit_reduction, 2) if credit_reduction is not None else None,
        "median_api_cost_reduction_percent": round(api_cost_reduction, 2) if api_cost_reduction is not None else None,
        "minimum_required_percent": 50.0,
        "pair_total_token_reductions_percent": pair_reductions,
        "all_pairs_positive": all(reduction > 0 for reduction in pair_reductions),
        "commands_not_increased": commands_not_increased,
        "usage_complete": usage_complete,
    }


def execute_three_run_ab(output_dir: Path, *, timeout: int = 1800, pair_count: int = 3) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    pairs = []
    selected_orders = RUN_ORDERS[:pair_count]
    for index, order in enumerate(selected_orders, start=1):
        results = {}
        for kind in order:
            with tempfile.TemporaryDirectory(prefix=f"contextguard-support-ab-{index}-{kind}-") as tmp:
                results[kind] = _run_one(kind, Path(tmp), output_dir / f"pair-{index}" / kind, timeout)
                results[kind]["sol_credits"] = sol_credit_cost(results[kind])
                results[kind]["api_cost_usd"] = api_cost_usd(results[kind])
        raw_core = {key: results["raw"]["validation"]["canonical_output"].get(key) for key in ("sku", "quantity", "remaining", "ok")}
        contextguard_core = {key: results["contextguard"]["validation"]["canonical_output"].get(key) for key in ("sku", "quantity", "remaining", "ok")}
        accepted = all([
                results["raw"]["validation"]["exit_code"] == 0,
                results["contextguard"]["validation"]["exit_code"] == 0,
                raw_core == contextguard_core == {"sku": "widget", "quantity": 3, "remaining": 7, "ok": True},
                results["raw"]["validation"]["concurrency_output"] == results["contextguard"]["validation"]["concurrency_output"],
                results["raw"]["validation"]["changelog_updated"],
                results["contextguard"]["validation"]["changelog_updated"],
                results["raw"]["exact_baseline_command"],
                results["contextguard"]["capture_runner_used"],
        ])
        pairs.append({"pair": index, "order": list(order), "accepted": accepted, **results})
    keys = ["input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "reasoning_output_tokens", "tool_output_bytes", "elapsed_seconds", "command_executions", "sol_credits", "api_cost_usd"]
    aggregate = {}
    for key in keys:
        raw_values = [pair["raw"][key] for pair in pairs]
        cg_values = [pair["contextguard"][key] for pair in pairs]
        raw_median = statistics.median(raw_values)
        cg_median = statistics.median(cg_values)
        aggregate[key] = {
            "raw_values": raw_values,
            "contextguard_values": cg_values,
            "raw_median": raw_median,
            "contextguard_median": cg_median,
            "median_change_percent": percent_change(raw_median, cg_median),
        }
    raw_totals = [int(pair["raw"]["input_tokens"]) + int(pair["raw"]["output_tokens"]) for pair in pairs]
    contextguard_totals = [
        int(pair["contextguard"]["input_tokens"]) + int(pair["contextguard"]["output_tokens"])
        for pair in pairs
    ]
    raw_total_median = statistics.median(raw_totals)
    contextguard_total_median = statistics.median(contextguard_totals)
    aggregate["total_tokens"] = {
        "raw_values": raw_totals,
        "contextguard_values": contextguard_totals,
        "raw_median": raw_total_median,
        "contextguard_median": contextguard_total_median,
        "median_change_percent": percent_change(raw_total_median, contextguard_total_median),
    }
    release_gate = build_release_gate(pairs, aggregate)
    result = {
        "benchmark": f"real-codex-human-support-ticket-{pair_count}-pair-ab",
        "model": BENCHMARK_MODEL, "reasoning_effort": REASONING_EFFORT,
        "run_orders": [list(order) for order in selected_orders],
        "optimized_runtime": {
            "tool_output_token_limit": os.environ.get("CONTEXTGUARD_TOOL_OUTPUT_TOKEN_LIMIT") or None,
            "model_verbosity": os.environ.get("CONTEXTGUARD_MODEL_VERBOSITY") or None,
            "auto_compact_token_limit": os.environ.get("CONTEXTGUARD_AUTO_COMPACT_TOKEN_LIMIT") or None,
        },
        "sol_credit_rates_per_million": SOL_CREDITS_PER_MILLION,
        "api_usd_rates_per_million": API_USD_PER_MILLION,
        "all_pairs_accepted": all(pair["accepted"] for pair in pairs),
        "release_gate": release_gate,
        "pairs": pairs, "aggregate": aggregate,
        "limitations": [
            f"{pair_count} controlled pair(s) do not eliminate model stochasticity.",
            "Hidden tests improve quality independence but cannot represent every production repository.",
            "Codex subscription quota accounting is not exposed by the CLI.",
            "The USD calculation uses standard GPT-5.6 Sol text-token pricing and assumes no individual request crossed the 272K long-context threshold.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=PLUGIN_ROOT / "benchmarks/results/real-codex-support-ab-2026-06-13")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--pairs", type=int, choices=(1, 3), default=3)
    args = parser.parse_args(argv)
    if args.self_check:
        with tempfile.TemporaryDirectory(prefix="contextguard-support-check-") as tmp:
            project = create_fixture(Path(tmp) / "fixture")
            before = validate_fixture(project)
            apply_reference_solution(project)
            after = validate_fixture(project)
            print(json.dumps({"before": before["exit_code"], "after": after["exit_code"], "hidden_passed": after["hidden_passed_tests"], "canonical": after["canonical_output"]}, sort_keys=True))
            return int(after["exit_code"] != 0)
    if args.run:
        result = execute_three_run_ab(args.output_dir, timeout=args.timeout, pair_count=args.pairs)
        print(json.dumps(result["aggregate"], indent=2, sort_keys=True))
        return int(not result["release_gate"]["passed"])
    parser.error("choose --self-check or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
