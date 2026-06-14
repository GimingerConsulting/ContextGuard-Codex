#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import tiktoken
except ModuleNotFoundError:  # Optional benchmark dependency.
    tiktoken = None

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from benchmarks.real_codex_ab import create_fixture


HOOK = PLUGIN_ROOT / "hooks" / "post_tool_use.py"
TOKENIZER = tiktoken.get_encoding("o200k_base") if tiktoken else None


def _tokens(text: str) -> int:
    if TOKENIZER:
        return len(TOKENIZER.encode(text))
    return (len(text.encode()) + 3) // 4


def _run_hook(raw_output: str, project: Path) -> tuple[dict, float]:
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=project,
        input=json.dumps({"tool_name": "Bash", "tool_response": raw_output}),
        text=True,
        capture_output=True,
        check=True,
    )
    elapsed = time.perf_counter() - started
    return json.loads(proc.stdout), elapsed


def compare_output(raw_output: str, project: Path, *, timing_samples: int = 7) -> dict:
    raw_token_times = []
    for _ in range(timing_samples):
        started = time.perf_counter()
        raw_tokens = _tokens(raw_output)
        raw_token_times.append(time.perf_counter() - started)

    hook_times = []
    result = {}
    for _ in range(timing_samples):
        result, elapsed = _run_hook(raw_output, project)
        hook_times.append(elapsed)

    visible = result["reason"]
    full_output_line = next(line for line in visible.splitlines() if line.startswith("full_output: "))
    archived_path = Path(full_output_line.removeprefix("full_output: "))
    if not archived_path.is_absolute():
        archived_path = project / archived_path
    archived = archived_path.read_text(encoding="utf-8")
    raw_hash = hashlib.sha256(raw_output.encode()).hexdigest()
    archived_hash = hashlib.sha256(archived.encode()).hexdigest()
    contextguard_tokens = _tokens(visible)
    summary_present = any(
        marker in visible for marker in ("failed in", "passed in", "error in", "errors in")
    )
    failed_test_present = "failed_tests:" in visible and "tests/" in visible
    equivalent = archived_hash == raw_hash and summary_present and failed_test_present
    return {
        "tokenizer": "o200k_base via tiktoken" if TOKENIZER else "estimated at four UTF-8 bytes per token",
        "raw_visible_bytes": len(raw_output.encode()),
        "contextguard_visible_bytes": len(visible.encode()),
        "raw_visible_tokens": raw_tokens,
        "contextguard_visible_tokens": contextguard_tokens,
        "tokens_saved": raw_tokens - contextguard_tokens,
        "token_reduction_percent": round((raw_tokens - contextguard_tokens) / raw_tokens * 100, 2),
        "raw_tokenization_seconds_median": round(statistics.median(raw_token_times), 6),
        "contextguard_hook_seconds_median": round(statistics.median(hook_times), 6),
        "contextguard_overhead_seconds": round(
            statistics.median(hook_times) - statistics.median(raw_token_times), 6
        ),
        "raw_output_sha256": raw_hash,
        "archived_output_sha256": archived_hash,
        "summary_present": summary_present,
        "failed_test_present": failed_test_present,
        "equivalent_information": equivalent,
        "visible_output": visible,
    }


def run_benchmark(output_path: Path, *, timing_samples: int = 7) -> dict:
    with tempfile.TemporaryDirectory(prefix="contextguard-output-ab-") as tmp:
        project = create_fixture(Path(tmp) / "hard-settlement")
        started = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=project,
            text=True,
            capture_output=True,
        )
        command_seconds = time.perf_counter() - started
        raw_output = proc.stdout + proc.stderr
        comparison = compare_output(raw_output, project, timing_samples=timing_samples)
        result = {
            "benchmark": "hard-130-failure-output-raw-vs-contextguard",
            "command": "python3 -m pytest -q",
            "exit_code": proc.returncode,
            "command_seconds": round(command_seconds, 6),
            "timing_samples": timing_samples,
            **comparison,
        }
        visible_summary = "\n".join(
            line
            for line in result["visible_output"].splitlines()
            if not line.startswith(("full_output: ", "summary: "))
        )
        stored_result = {key: value for key, value in result.items() if key != "visible_output"}
        stored_result["visible_summary"] = visible_summary
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(stored_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PLUGIN_ROOT / "benchmarks" / "results" / "output-ab-2026-06-10.json",
    )
    parser.add_argument("--timing-samples", type=int, default=7)
    args = parser.parse_args(argv)
    result = run_benchmark(args.output, timing_samples=args.timing_samples)
    print(json.dumps({key: value for key, value in result.items() if key != "visible_output"}, indent=2, sort_keys=True))
    return int(not result["equivalent_information"] or result["tokens_saved"] <= 0)


if __name__ == "__main__":
    raise SystemExit(main())
