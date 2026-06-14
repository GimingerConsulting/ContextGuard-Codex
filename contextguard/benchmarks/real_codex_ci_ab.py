#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
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
    _write,
    parse_codex_jsonl,
    percent_change,
    prepare_codex_home,
    prepare_optimized_project,
    repository_hash,
)


PROMPT = """Please investigate and resolve the CI failure described in PR_REVIEW.md.

Treat this as a normal pull-request maintenance task:
- before editing, run `python3 -m pytest -q` exactly once and follow repository instructions for safe command execution
- inspect artifacts/CI_FAILURE.log and reproduce the reported failure locally
- identify the root cause; do not hard-code the examples from the log
- preserve the existing `reporting.daily_counts(events, timezone_name)` public API
- add focused regression coverage and update CHANGELOG.md
- run the complete test suite and useful targeted checks

Do not weaken or remove tests. Finish only after the CI behavior is fixed and validation passes.
"""

RUN_ORDERS = [("raw", "contextguard"), ("contextguard", "raw")]

PR_REVIEW = """# PR review: analytics dependency refresh

The Linux CI job is red although the local suite is green. Daily order totals are assigned to the wrong calendar day for customers outside UTC, especially around daylight-saving transitions. The attached CI log contains representative failures from several regions.

Please reproduce the issue, fix the underlying date-bucketing behavior without changing the public API, add regression coverage, and add a changelog entry.
"""

INITIAL_FILES = {
    "pyproject.toml": """[build-system]\nrequires=[\"setuptools>=68\"]\nbuild-backend=\"setuptools.build_meta\"\n\n[project]\nname=\"daily-reporting\"\nversion=\"2.4.1\"\nrequires-python=\">=3.9\"\n\n[tool.pytest.ini_options]\ntestpaths=[\"tests\"]\npythonpath=[\".\"]\n""",
    "reporting/__init__.py": "from .buckets import daily_counts\n\n__all__ = [\"daily_counts\"]\n",
    "reporting/buckets.py": """def daily_counts(events, timezone_name):
    counts = {}
    for event in events:
        day = event["created_at"][:10]
        counts[day] = counts.get(day, 0) + 1
    return dict(sorted(counts.items()))
""",
    "reporting/cli.py": """import json
import sys
from pathlib import Path

from .buckets import daily_counts


def main():
    payload = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(daily_counts(payload["events"], payload["timezone"]), sort_keys=True))


if __name__ == "__main__":
    main()
""",
    "tests/test_public.py": """from reporting import daily_counts


def test_empty_events():
    assert daily_counts([], "UTC") == {}


def test_simple_utc_days_are_counted():
    events = [{"created_at": "2026-01-01T10:00:00Z"}, {"created_at": "2026-01-01T12:00:00Z"}]
    assert daily_counts(events, "UTC") == {"2026-01-01": 2}


def test_output_days_are_sorted():
    events = [{"created_at": "2026-01-02T00:00:00Z"}, {"created_at": "2026-01-01T00:00:00Z"}]
    assert list(daily_counts(events, "UTC")) == ["2026-01-01", "2026-01-02"]
""",
    "scenario.json": json.dumps({"timezone": "America/New_York", "events": [
        {"created_at": "2026-03-08T06:30:00Z"},
        {"created_at": "2026-03-08T07:30:00Z"},
        {"created_at": "2026-03-09T04:30:00Z"},
    ]}, indent=2) + "\n",
    "PR_REVIEW.md": PR_REVIEW,
    "CHANGELOG.md": "# Changelog\n\n## Unreleased\n\n",
}

REFERENCE_FILE = """from datetime import datetime
from zoneinfo import ZoneInfo


def daily_counts(events, timezone_name):
    timezone = ZoneInfo(timezone_name)
    counts = {}
    for event in events:
        value = event["created_at"]
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        day = datetime.fromisoformat(value).astimezone(timezone).date().isoformat()
        counts[day] = counts.get(day, 0) + 1
    return dict(sorted(counts.items()))
"""

HIDDEN_TESTS = r'''from datetime import datetime, timedelta, timezone

import pytest

from reporting import daily_counts


@pytest.mark.parametrize("index", range(64))
def test_new_york_local_day_matches_timezone(index):
    instant = datetime(2026, 3, 8, 4, 0, tzinfo=timezone.utc) + timedelta(minutes=index * 30)
    value = instant.isoformat().replace("+00:00", "Z")
    expected = instant.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
    assert daily_counts([{"created_at": value}], "America/New_York") == {expected: 1}


@pytest.mark.parametrize("index", range(64))
def test_berlin_local_day_matches_timezone(index):
    instant = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=index * 30)
    value = instant.isoformat().replace("+00:00", "Z")
    expected = instant.astimezone(__import__("zoneinfo").ZoneInfo("Europe/Berlin")).date().isoformat()
    assert daily_counts([{"created_at": value}], "Europe/Berlin") == {expected: 1}


@pytest.mark.parametrize("index", range(32))
def test_offset_timestamps_and_sorted_aggregation(index):
    events = [
        {"created_at": f"2026-01-{(index % 9) + 1:02d}T23:30:00-08:00"},
        {"created_at": f"2026-01-{(index % 9) + 2:02d}T02:30:00-05:00"},
    ]
    result = daily_counts(events, "UTC")
    assert sum(result.values()) == 2
    assert list(result) == sorted(result)
'''


def create_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in INITIAL_FILES.items():
        _write(root / relative, content)
    failures = []
    zones = ["America/New_York", "Europe/Berlin", "Asia/Tokyo", "Australia/Sydney"]
    for index in range(14000):
        zone = zones[index % len(zones)]
        failures.append(
            f"FAILED tests/test_daily_ci.py::test_local_bucket[{zone}-{index}] "
            f"expected=2026-03-{(index % 20) + 1:02d} actual=2026-03-{(index % 20) + 2:02d} "
            f"created_at=2026-03-{(index % 20) + 1:02d}T23:30:00Z"
        )
    _write(root / "artifacts/CI_FAILURE.log", "\n".join(failures) + "\n160 failed, 3 passed in 8.42s\n")
    _write(root / ".gitignore", ".contextguard/\n__pycache__/\n.pytest_cache/\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "ContextGuard Benchmark"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "reporting service before CI fix"], cwd=root, check=True)
    return root


def apply_reference_solution(root: Path) -> None:
    _write(root / "reporting/buckets.py", REFERENCE_FILE)
    _write(root / "CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n- Bucket daily reports in the requested customer timezone.\n")


def _canonical(root: Path) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, "-m", "reporting.cli", "scenario.json"], cwd=root, text=True, capture_output=True)
    try:
        value = json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        value = {}
    return proc.returncode, value


def validate_fixture(root: Path) -> dict:
    public = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=root, text=True, capture_output=True)
    with tempfile.TemporaryDirectory(prefix="contextguard-hidden-ci-") as tmp:
        hidden = Path(tmp) / "test_hidden_ci.py"
        hidden.write_text(HIDDEN_TESTS, encoding="utf-8")
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", str(hidden)], cwd=root, text=True, capture_output=True)
    output = proc.stdout + proc.stderr
    passed = re.search(r"(\d+) passed", output)
    failed = re.search(r"(\d+) failed", output)
    canonical_exit, canonical = _canonical(root)
    return {
        "exit_code": proc.returncode,
        "public_exit_code": public.returncode,
        "passed_tests": int(passed.group(1)) if passed else 0,
        "failed_tests": int(failed.group(1)) if failed else (0 if proc.returncode == 0 else 1),
        "hidden_passed_tests": 160 if proc.returncode == 0 else 0,
        "hidden_failed_tests": 0 if proc.returncode == 0 else 160,
        "collected_tests": 163,
        "output": output,
        "canonical_exit_code": canonical_exit,
        "canonical_output": canonical,
        "changelog_updated": len((root / "CHANGELOG.md").read_text().splitlines()) > 4,
    }


def build_codex_command(project: Path, *, optimized: bool, model: str = "gpt-5.5") -> list[str]:
    command = shlex.split(os.environ.get("CONTEXTGUARD_CODEX_COMMAND", "codex"))
    command.extend([
        "exec", "--json", "--ephemeral", "--ignore-rules", "--model", model,
        "-c", 'model_reasoning_effort="medium"', "--sandbox", "danger-full-access",
        "-c", 'approval_policy="never"', "-c", "features.plugins=false", "-C", str(project), PROMPT,
    ])
    return command


def run_trial(
    project: Path,
    home: Path,
    artifact_dir: Path,
    *,
    optimized: bool,
    timeout: int,
    model: str = "gpt-5.5",
) -> dict:
    prepare_codex_home(home, project)
    if optimized:
        prepare_optimized_project(project)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(home)
    import time
    started = time.perf_counter()
    try:
        proc = subprocess.run(build_codex_command(project, optimized=optimized, model=model), cwd=project, env=environment, text=True, capture_output=True, timeout=timeout)
        stdout, stderr, exit_code, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, exit_code, timed_out = exc.stdout or "", exc.stderr or "", 124, True
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
    parsed = parse_codex_jsonl(stdout)
    parsed["exact_baseline_command"] = any("python3 -m pytest -q" in command for command in parsed["commands"])
    parsed["capture_runner_used"] = any(
        ".contextguard/bin/contextguard" in command and "capture" in command and "python3 -m pytest -q" in command
        for command in parsed["commands"]
    )
    validation = validate_fixture(project)
    diff = subprocess.run(["git", "diff", "--", ".", ":(exclude)AGENTS.md", ":(exclude)docs"], cwd=project, text=True, capture_output=True).stdout
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
    }


def execute_ab(output_dir: Path, *, timeout: int = 1800, model: str = "gpt-5.5") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    pairs = []
    for index, order in enumerate(RUN_ORDERS, start=1):
        results = {}
        for kind in order:
            with tempfile.TemporaryDirectory(prefix=f"contextguard-ci-ab-{index}-{kind}-") as tmp:
                root = Path(tmp)
                project = create_fixture(root / "project")
                results[kind] = run_trial(project, root / "home", output_dir / f"pair-{index}" / kind, optimized=kind == "contextguard", timeout=timeout, model=model)
        accepted = all([
            results["raw"]["validation"]["exit_code"] == 0,
            results["contextguard"]["validation"]["exit_code"] == 0,
            results["raw"]["validation"]["canonical_output"] == results["contextguard"]["validation"]["canonical_output"],
            results["raw"]["validation"]["changelog_updated"],
            results["contextguard"]["validation"]["changelog_updated"],
            results["raw"]["exact_baseline_command"], results["contextguard"]["capture_runner_used"],
        ])
        pairs.append({"pair": index, "order": list(order), "accepted": accepted, **results})
    keys = ["input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "reasoning_output_tokens", "tool_output_bytes", "elapsed_seconds", "command_executions"]
    aggregate = {}
    for key in keys:
        raw_values = [pair["raw"][key] for pair in pairs]
        cg_values = [pair["contextguard"][key] for pair in pairs]
        raw_median, cg_median = statistics.median(raw_values), statistics.median(cg_values)
        aggregate[key] = {"raw_values": raw_values, "contextguard_values": cg_values, "raw_median": raw_median, "contextguard_median": cg_median, "median_change_percent": percent_change(raw_median, cg_median)}
    result = {"benchmark": "real-codex-human-ci-investigation-ab", "model": model, "reasoning_effort": "medium", "run_orders": [list(order) for order in RUN_ORDERS], "all_pairs_accepted": all(pair["accepted"] for pair in pairs), "pairs": pairs, "aggregate": aggregate, "limitations": ["Two pairs expose order effects but model execution remains stochastic.", "Codex subscription quota accounting is not exposed by the CLI."]}
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=PLUGIN_ROOT / "benchmarks/results/real-codex-ci-ab-2026-06-14")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--model", default="gpt-5.5")
    args = parser.parse_args(argv)
    if args.self_check:
        with tempfile.TemporaryDirectory(prefix="contextguard-ci-check-") as tmp:
            project = create_fixture(Path(tmp) / "fixture")
            before = validate_fixture(project)
            apply_reference_solution(project)
            after = validate_fixture(project)
            print(json.dumps({"before": before["exit_code"], "public_before": before["public_exit_code"], "after": after["exit_code"], "hidden_passed": after["hidden_passed_tests"], "canonical": after["canonical_output"]}, sort_keys=True))
            return int(after["exit_code"] != 0)
    if args.run:
        result = execute_ab(args.output_dir, timeout=args.timeout, model=args.model)
        print(json.dumps(result["aggregate"], indent=2, sort_keys=True))
        return int(not result["all_pairs_accepted"])
    parser.error("choose --self-check or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
