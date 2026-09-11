#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from benchmarks.real_codex_ab import parse_codex_jsonl, percent_change, repository_hash
from contextguard.codex_usage import (
    MODEL_PRICES,
    PRICING_LAST_VERIFIED,
    PRICING_SOURCE,
    calculate_turn_cost,
    canonical_model,
)

DEFAULT_MODEL = os.environ.get("CONTEXTGUARD_BENCHMARK_MODEL", "gpt-5.5")
DEFAULT_REASONING_EFFORT = os.environ.get("CONTEXTGUARD_BENCHMARK_REASONING_EFFORT", "medium")


PROMPT = """Fix and complete the production inventory reservation service described in SPEC.md.

This is an existing backend service, not a greenfield rewrite. Requirements:
- before editing, run `python3 -m pytest -q` exactly once and follow the repository instructions for safe command execution
- on the optimized run, when `.contextguard/bin/contextguard` exists, route the full test suite and broad log/data listings through that capture runner; keep focused source reads direct and do not combine source reads with noisy output
- preserve the backward-compatible v1 response keys while adding the v2 fields
- implement the legacy schema-version-1 to schema-version-2 migration without losing stock
- make request IDs idempotent, including repeated calls after a successful reservation
- reject stale expected versions without modifying inventory
- make concurrent reservations thread-safe so stock can never become negative
- emit deterministic structured JSON audit logs without timestamps or nondeterministic ordering
- preserve the public API exposed by `inventory.api.handle_request`
- run the complete test suite and fix all failures

Do not weaken, delete, or skip tests. Do not replace the test suite. Work directly in the repository and finish only when all validation passes.
"""


INITIAL_FILES = {
    "pyproject.toml": """[build-system]
requires=["setuptools>=68"]
build-backend="setuptools.build_meta"

[project]
name="inventory-service"
version="1.7.0"
requires-python=">=3.9"

[tool.pytest.ini_options]
testpaths=["tests"]
pythonpath=["."]
""",
    "SPEC.md": """# Inventory Reservation Service Upgrade

The existing `inventory.api.handle_request(payload, service)` API must remain available.

1. Legacy records use `{sku, quantity}` and implicit schema version 1. Migration returns schema version 2 records with `{sku, available, reserved, version, schema_version}`. Existing schema-2 records are normalized without changing values.
2. `reserve(sku, quantity, request_id, expected_version=None)` accepts positive integer quantities only.
3. Successful reservations decrement available stock, increment reserved stock and version, and return status `reserved`. Insufficient stock returns `rejected` without mutation.
4. Repeated request IDs return the original response byte-for-byte and never mutate state again.
5. A mismatching expected version returns status `conflict`, includes the current version, and does not mutate state.
6. Concurrent calls must be atomic and stock may never become negative.
7. Keep v1 keys `sku`, `quantity`, `remaining`, `ok`; add v2 keys `request_id`, `status`, `available`, `reserved`, `version`.
8. Audit entries are deterministic sorted-key JSON containing event, request_id, sku, quantity, status, available, reserved and version. No timestamp is allowed.
9. CLI commands `reserve scenario.json` and `migrate legacy-db.json` print sorted JSON.
""",
    "inventory/__init__.py": "from .api import handle_request\nfrom .service import InventoryService\n\n__all__ = [\"handle_request\", \"InventoryService\"]\n",
    "inventory/migration.py": """def migrate_record(record):
    # BUG: legacy quantity is discarded and version metadata is missing.
    return {"sku": record["sku"], "available": 0, "reserved": 0}
""",
    "inventory/audit.py": """import json
import time


def audit_line(payload):
    payload = dict(payload)
    payload["timestamp"] = time.time()
    return json.dumps(payload)
""",
    "inventory/service.py": """from .audit import audit_line
from .migration import migrate_record


class InventoryService:
    def __init__(self, records):
        self.records = {item["sku"]: migrate_record(item) for item in records}
        self.seen = {}
        self.audit = []

    def reserve(self, sku, quantity, request_id, expected_version=None):
        record = self.records[sku]
        record["available"] -= quantity
        result = {"sku": sku, "quantity": quantity, "remaining": record["available"], "ok": True}
        self.audit.append(audit_line(result))
        return result
""",
    "inventory/api.py": """def handle_request(payload, service):
    return service.reserve(payload["sku"], payload["quantity"], payload.get("request_id", "legacy"))
""",
    "inventory/cli.py": """import json
import sys
from pathlib import Path

from .api import handle_request
from .migration import migrate_record
from .service import InventoryService


def main():
    command, path = sys.argv[1], Path(sys.argv[2])
    payload = json.loads(path.read_text())
    if command == "migrate":
        result = migrate_record(payload)
    else:
        service = InventoryService(payload["records"])
        result = handle_request(payload["request"], service)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
""",
    "legacy-db.json": json.dumps({"sku": "widget", "quantity": 10, "schema_version": 1}, indent=2) + "\n",
    "scenario.json": json.dumps({"records": [{"sku": "widget", "quantity": 10}], "request": {"sku": "widget", "quantity": 3, "request_id": "req-001", "expected_version": 0}}, indent=2) + "\n",
}


REFERENCE_FILES = {
    "inventory/migration.py": """def migrate_record(record):
    if int(record.get("schema_version", 1)) == 1:
        return {"sku": record["sku"], "available": int(record["quantity"]), "reserved": 0, "version": 0, "schema_version": 2}
    return {
        "sku": record["sku"],
        "available": int(record["available"]),
        "reserved": int(record.get("reserved", 0)),
        "version": int(record.get("version", 0)),
        "schema_version": 2,
    }
""",
    "inventory/audit.py": """import json


def audit_line(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
""",
    "inventory/service.py": """import threading

from .audit import audit_line
from .migration import migrate_record


class InventoryService:
    def __init__(self, records):
        self.records = {item["sku"]: migrate_record(item) for item in records}
        self.seen = {}
        self.audit = []
        self._lock = threading.RLock()

    def reserve(self, sku, quantity, request_id, expected_version=None):
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        with self._lock:
            if request_id in self.seen:
                return dict(self.seen[request_id])
            record = self.records[sku]
            if expected_version is not None and int(expected_version) != record["version"]:
                status, ok = "conflict", False
            elif quantity > record["available"]:
                status, ok = "rejected", False
            else:
                record["available"] -= quantity
                record["reserved"] += quantity
                record["version"] += 1
                status, ok = "reserved", True
            result = {
                "sku": sku, "quantity": quantity, "remaining": record["available"], "ok": ok,
                "request_id": request_id, "status": status, "available": record["available"],
                "reserved": record["reserved"], "version": record["version"],
            }
            self.seen[request_id] = dict(result)
            self.audit.append(audit_line({
                "event": "inventory_reservation", "request_id": request_id, "sku": sku,
                "quantity": quantity, "status": status, "available": record["available"],
                "reserved": record["reserved"], "version": record["version"],
            }))
            return result
""",
    "inventory/api.py": """def handle_request(payload, service):
    return service.reserve(
        payload["sku"], payload["quantity"], payload.get("request_id", "legacy"),
        payload.get("expected_version"),
    )
""",
}


TEST_FILE = r'''import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from inventory.api import handle_request
from inventory.audit import audit_line
from inventory.migration import migrate_record
from inventory.service import InventoryService


@pytest.mark.parametrize("quantity", range(1, 129))
def test_migrates_legacy_stock_without_loss(quantity):
    result = migrate_record({"sku": f"sku-{quantity}", "quantity": quantity, "schema_version": 1})
    assert result == {"sku": f"sku-{quantity}", "available": quantity, "reserved": 0, "version": 0, "schema_version": 2}


@pytest.mark.parametrize("quantity", range(1, 97))
def test_idempotent_reservation_returns_original_result(quantity):
    service = InventoryService([{"sku": "widget", "quantity": quantity + 10}])
    first = service.reserve("widget", quantity, f"req-{quantity}")
    second = service.reserve("widget", quantity, f"req-{quantity}")
    assert first == second
    assert service.records["widget"]["available"] == 10
    assert service.records["widget"]["reserved"] == quantity
    assert len(service.audit) == 1


@pytest.mark.parametrize("quantity", range(1, 65))
def test_backward_compatible_api_and_v2_fields(quantity):
    service = InventoryService([{"sku": "widget", "quantity": 100}])
    result = handle_request({"sku": "widget", "quantity": quantity, "request_id": f"api-{quantity}", "expected_version": 0}, service)
    assert result["sku"] == "widget"
    assert result["quantity"] == quantity
    assert result["remaining"] == 100 - quantity
    assert result["ok"] is True
    assert result["status"] == "reserved"
    assert result["available"] == 100 - quantity
    assert result["reserved"] == quantity
    assert result["version"] == 1


@pytest.mark.parametrize("available", range(1, 33))
def test_insufficient_stock_and_version_conflict_do_not_mutate(available):
    service = InventoryService([{"sku": "widget", "quantity": available}])
    rejected = service.reserve("widget", available + 1, f"reject-{available}")
    conflict = service.reserve("widget", 1, f"conflict-{available}", expected_version=9)
    assert rejected["status"] == "rejected"
    assert conflict["status"] == "conflict"
    assert service.records["widget"]["available"] == available
    assert service.records["widget"]["reserved"] == 0
    assert service.records["widget"]["version"] == 0


def test_concurrent_reservations_are_atomic():
    service = InventoryService([{"sku": "widget", "quantity": 20}])
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda index: service.reserve("widget", 1, f"parallel-{index}"), range(40)))
    assert sum(item["ok"] for item in results) == 20
    assert service.records["widget"]["available"] == 0
    assert service.records["widget"]["reserved"] == 20
    assert service.records["widget"]["version"] == 20


def test_audit_is_deterministic_json_without_timestamp():
    payload = {"event": "inventory_reservation", "request_id": "r", "sku": "w", "quantity": 1, "status": "reserved", "available": 9, "reserved": 1, "version": 1}
    line = audit_line(payload)
    assert line == audit_line(payload)
    assert "timestamp" not in line
    assert json.loads(line) == payload


@pytest.mark.parametrize("invalid", [0, -1, -99, 1.5, "2", None, True])
def test_invalid_quantity_is_rejected(invalid):
    service = InventoryService([{"sku": "widget", "quantity": 10}])
    with pytest.raises(ValueError):
        service.reserve("widget", invalid, "invalid")
'''


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in INITIAL_FILES.items():
        _write(root / relative, content)
    _write(root / "tests/test_inventory.py", TEST_FILE)
    _write(root / "data/production.log", "\n".join(
        f"ERROR reservation conflict request=req-{index % 701} sku=sku-{index % 113} version={index % 17}"
        for index in range(25000)
    ))
    _write(root / "data/orders.jsonl", "\n".join(
        json.dumps({"order_id": index, "sku": f"sku-{index % 113}", "quantity": index % 9 + 1, "state": "historical"})
        for index in range(15000)
    ))
    _write(root / ".gitignore", ".contextguard/\n__pycache__/\n.pytest_cache/\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "ContextGuard Benchmark"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial legacy inventory service"], cwd=root, check=True)
    return root


def apply_reference_solution(root: Path) -> None:
    for relative, content in REFERENCE_FILES.items():
        _write(root / relative, content)


def _json_command(root: Path, *args: str) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, "-m", "inventory.cli", *args], cwd=root, text=True, capture_output=True)
    try:
        payload = json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        payload = {}
    return proc.returncode, payload


def _concurrency_probe(root: Path) -> dict:
    code = '''import json
from concurrent.futures import ThreadPoolExecutor
from inventory.service import InventoryService
s = InventoryService([{"sku": "widget", "quantity": 10}])
with ThreadPoolExecutor(max_workers=20) as pool:
    results = list(pool.map(lambda i: s.reserve("widget", 1, f"probe-{i}"), range(20)))
print(json.dumps({"successful": sum(item["ok"] for item in results), "available": s.records["widget"]["available"], "reserved": s.records["widget"]["reserved"], "version": s.records["widget"]["version"]}, sort_keys=True))
'''
    proc = subprocess.run([sys.executable, "-c", code], cwd=root, text=True, capture_output=True)
    try:
        return json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        return {}


def validate_fixture(root: Path) -> dict:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, text=True, capture_output=True)
    output = proc.stdout + proc.stderr
    passed = re.search(r"(\d+) passed", output)
    failed = re.search(r"(\d+) failed", output)
    canonical_exit, canonical = _json_command(root, "reserve", "scenario.json")
    migration_exit, migration = _json_command(root, "migrate", "legacy-db.json")
    return {
        "exit_code": proc.returncode,
        "passed_tests": int(passed.group(1)) if passed else 0,
        "failed_tests": int(failed.group(1)) if failed else (0 if proc.returncode == 0 else 1),
        "collected_tests": 329,
        "output": output,
        "canonical_exit_code": canonical_exit,
        "canonical_output": canonical,
        "migration_exit_code": migration_exit,
        "migration_output": migration,
        "concurrency_output": _concurrency_probe(root),
    }


def build_codex_command(
    project: Path,
    *,
    optimized: bool,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> list[str]:
    command = shlex.split(os.environ.get("CONTEXTGUARD_CODEX_COMMAND", "codex"))
    selected_model = model or DEFAULT_MODEL
    selected_effort = reasoning_effort or DEFAULT_REASONING_EFFORT
    command.extend([
        "exec", "--json", "--ephemeral", "--ignore-rules",
        "--model", selected_model, "-c", f'model_reasoning_effort="{selected_effort}"',
        "--sandbox", "danger-full-access", "-c", 'approval_policy="never"',
        "-c", f"features.plugins={'true' if optimized else 'false'}",
        "-C", str(project), PROMPT,
    ])
    return command


def prepare_codex_home(home: Path, project: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    auth = Path.home() / ".codex" / "auth.json"
    if not auth.exists():
        raise RuntimeError("Codex authentication is unavailable at ~/.codex/auth.json")
    shutil.copy2(auth, home / "auth.json")
    os.chmod(home / "auth.json", 0o600)
    canonical = Path(os.path.realpath(project))
    config = f'[projects."{canonical.as_posix()}"]\ntrust_level = "trusted"\n'
    (home / "config.toml").write_text(config, encoding="utf-8")


def prepare_optimized_project(project: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PLUGIN_ROOT)
    subprocess.run(
        [sys.executable, "-m", "contextguard.cli", "init", "--path", str(project)],
        cwd=PLUGIN_ROOT, env=environment, check=True, text=True, capture_output=True,
    )


def prepare_optimized_project_with_hooks(project: Path) -> None:
    prepare_optimized_project(project)
    hooks = json.loads((PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
    prefix = f"PYTHONPATH={shlex.quote(str(PLUGIN_ROOT))} "
    for rules in hooks.get("hooks", {}).values():
        for rule in rules:
            for hook in rule.get("hooks", []):
                if hook.get("type") == "command" and hook.get("command"):
                    hook["command"] = prefix + str(hook["command"]).replace("$PLUGIN_ROOT", str(PLUGIN_ROOT))
    config_dir = project / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "hooks.json").write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")


def run_trial(
    project: Path,
    home: Path,
    artifact_dir: Path,
    *,
    optimized: bool,
    timeout: int,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    prepare_codex_home(home, project)
    if optimized:
        prepare_optimized_project_with_hooks(project)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(home)
    started = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            build_codex_command(
                project,
                optimized=optimized,
                model=model,
                reasoning_effort=reasoning_effort,
            ), cwd=project, env=environment,
            text=True, capture_output=True, timeout=timeout,
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr, exit_code = exc.stdout or "", exc.stderr or "", 124
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
    parsed = parse_codex_jsonl(stdout)
    selected_model = canonical_model(model or DEFAULT_MODEL)
    cost, context_class = calculate_turn_cost(
        selected_model,
        {
            "input_tokens": parsed["input_tokens"],
            "cached_input_tokens": parsed["cached_input_tokens"],
            "cache_write_input_tokens": parsed.get("cache_write_input_tokens", 0),
            "output_tokens": parsed["output_tokens"],
        },
    )
    parsed["api_cost_usd"] = round(cost, 6) if cost is not None else None
    parsed["api_cost_context_class"] = context_class
    parsed["exact_baseline_command"] = any(
        command.endswith("'python3 -m pytest -q'") or command == "python3 -m pytest -q"
        for command in parsed["commands"]
    )
    parsed["capture_runner_used"] = any(
        ".contextguard/bin/contextguard" in command and "capture" in command and "python3 -m pytest -q" in command
        for command in parsed["commands"]
    )
    validation = validate_fixture(project)
    diff = subprocess.run(
        ["git", "diff", "--", ".", ":(exclude)AGENTS.md", ":(exclude)docs"],
        cwd=project, text=True, capture_output=True,
    ).stdout
    (artifact_dir / "events.jsonl").write_text(stdout, encoding="utf-8")
    (artifact_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    (artifact_dir / "final-response.txt").write_text(parsed["final_response"], encoding="utf-8")
    (artifact_dir / "diff.patch").write_text(diff, encoding="utf-8")
    (artifact_dir / "validation.txt").write_text(validation["output"], encoding="utf-8")
    return {
        "optimized": optimized, "codex_exit_code": exit_code, "timed_out": timed_out,
        "elapsed_seconds": round(time.perf_counter() - started, 3), **parsed,
        "validation": {key: value for key, value in validation.items() if key != "output"},
        "repository_hash": repository_hash(project), "diff_bytes": len(diff.encode()),
        "stderr_bytes": len(stderr.encode()),
    }


def execute_real_ab(
    output_dir: Path,
    *,
    timeout: int = 1800,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> dict:
    selected_model = canonical_model(model)
    if selected_model not in MODEL_PRICES:
        supported = ", ".join(sorted(MODEL_PRICES))
        raise ValueError(f"unsupported benchmark model {model!r}; choose one of: {supported}")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="contextguard-real-backend-ab-") as tmp:
        root = Path(tmp)
        raw_project = create_fixture(root / "raw-project")
        optimized_project = create_fixture(root / "contextguard-project")
        raw = run_trial(
            raw_project, root / "raw-home", output_dir / "raw", optimized=False,
            timeout=timeout, model=selected_model, reasoning_effort=reasoning_effort,
        )
        optimized = run_trial(
            optimized_project, root / "contextguard-home", output_dir / "contextguard", optimized=True,
            timeout=timeout, model=selected_model, reasoning_effort=reasoning_effort,
        )
        equivalent = all([
            raw["validation"]["exit_code"] == 0,
            optimized["validation"]["exit_code"] == 0,
            raw["validation"]["canonical_output"] == optimized["validation"]["canonical_output"],
            raw["validation"]["migration_output"] == optimized["validation"]["migration_output"],
            raw["validation"]["concurrency_output"] == optimized["validation"]["concurrency_output"],
            raw["validation"]["passed_tests"] == optimized["validation"]["passed_tests"],
            raw["exact_baseline_command"],
            optimized["capture_runner_used"],
        ])
        keys = [
            "input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens",
            "reasoning_output_tokens", "tool_output_bytes", "elapsed_seconds", "command_executions",
            "file_changes", "final_response_bytes", "diff_bytes", "api_cost_usd",
        ]
        comparison = {
            key: {"raw": raw[key], "contextguard": optimized[key], "change_percent": percent_change(raw[key], optimized[key])}
            for key in keys
        }
        result = {
            "benchmark": "real-codex-production-backend-ab", "model": selected_model,
            "reasoning_effort": reasoning_effort,
            "api_usd_rates_per_million": MODEL_PRICES[selected_model]["short"],
            "api_usd_rates_per_million_by_context": MODEL_PRICES[selected_model],
            "pricing_source": PRICING_SOURCE,
            "pricing_last_verified": PRICING_LAST_VERIFIED,
            "pricing_basis": "OpenAI Standard API, per-turn short/long context pricing",
            "codex_cli": subprocess.run(
                [*shlex.split(os.environ.get("CONTEXTGUARD_CODEX_COMMAND", "codex")), "--version"],
                text=True, capture_output=True,
            ).stdout.strip(),
            "same_prompt": True, "equivalent_result": equivalent, "raw": raw,
            "contextguard": optimized, "comparison": comparison,
            "limitations": [
                "Single controlled sample; model execution is stochastic.",
                "Codex subscription quota accounting is not exposed by the CLI.",
                "Cached and uncached input are reported separately.",
            ],
        }
        (output_dir / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--output-dir", type=Path,
        default=PLUGIN_ROOT / "benchmarks/results/real-codex-backend-ab-2026-06-13",
    )
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(MODEL_PRICES))
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=("none", "low", "medium", "high", "xhigh", "max"),
    )
    args = parser.parse_args(argv)
    if args.self_check:
        with tempfile.TemporaryDirectory(prefix="contextguard-backend-self-check-") as tmp:
            fixture = create_fixture(Path(tmp) / "fixture")
            before = validate_fixture(fixture)
            apply_reference_solution(fixture)
            after = validate_fixture(fixture)
            print(json.dumps({
                "before": before["exit_code"], "after": after["exit_code"],
                "tests": after["passed_tests"], "canonical": after["canonical_output"],
                "migration": after["migration_output"], "concurrency": after["concurrency_output"],
            }, sort_keys=True))
            return int(after["exit_code"] != 0)
    if args.run:
        result = execute_real_ab(
            args.output_dir,
            timeout=args.timeout,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
        print(json.dumps(result["comparison"], indent=2, sort_keys=True))
        return int(not result["equivalent_result"])
    parser.error("choose --self-check or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
