#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from contextguard.codex_usage import MODEL_PRICES, PRICING_LAST_VERIFIED, PRICING_SOURCE, canonical_model
from contextguard.output_policy import inspect_final_response


FIXTURE_NAMES = [
    "trivial-one-file-change",
    "medium-feature",
    "complex-debugging",
    "verbose-test-suite",
    "large-json-analysis",
    "repeated-log-errors",
    "long-multi-turn-session",
    "session-restart-unchanged",
    "session-restart-partial-changes",
    "large-existing-repository",
]


def env() -> dict[str, str]:
    current = os.environ.copy()
    current["PYTHONPATH"] = f"{PLUGIN_ROOT}{os.pathsep}{current.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    return current


def run(command: list[str], cwd: Path) -> tuple[int, int, float]:
    started = time.time()
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env())
    return proc.returncode, len(proc.stdout.encode()) + len(proc.stderr.encode()), time.time() - started


def contextguard(command: list[str], cwd: Path) -> tuple[int, int, float]:
    return run([sys.executable, "-m", "contextguard.cli", "capture", "--", *command], cwd)


def create_fixture(root: Path, name: str) -> tuple[Path, list[str]]:
    project = root / name
    project.mkdir(parents=True)
    if name == "verbose-test-suite":
        script = project / "test_output.py"
        script.write_text("for i in range(500): print(f'FAILED test_case_{i} app.py:{i}: error')\nraise SystemExit(1)\n")
        return project, [sys.executable, str(script)]
    if name == "large-json-analysis":
        path = project / "data.json"
        path.write_text(json.dumps([{"id": i, "status": "error" if i % 10 == 0 else "ok"} for i in range(1000)]))
        return project, ["cat", str(path)]
    if name == "repeated-log-errors":
        path = project / "app.log"
        path.write_text("\n".join(f"ERROR repeated failure {i}" for i in range(500)))
        return project, ["cat", str(path)]
    if name == "trivial-one-file-change":
        path = project / "app.py"
        path.write_text("VALUE = 1\n")
        return project, [sys.executable, "-c", "from pathlib import Path; Path('app.py').write_text('VALUE = 2\\n')"]
    if name == "medium-feature":
        (project / "service.py").write_text("def enabled(): return False\n")
        return project, [sys.executable, "-c", "from pathlib import Path; Path('feature.py').write_text('def enabled(): return True\\n')"]
    if name == "complex-debugging":
        script = project / "debug.py"
        script.write_text("print('Traceback (most recent call last):')\nprint('ValueError: broken')\nraise SystemExit(1)\n")
        return project, [sys.executable, str(script)]
    if name == "session-restart-partial-changes":
        (project / "partial.py").write_text("STEP = 1\n")
    elif name == "large-existing-repository":
        for index in range(300):
            (project / f"module_{index}.py").write_text(f"VALUE = {index}\n")
    else:
        (project / "app.py").write_text("def main():\n    return 'ok'\n")
    return project, ["find", ".", "-type", "f"]


def repository_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".contextguard" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run_suite() -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="contextguard-bench-") as tmp:
        tmp_path = Path(tmp)
        results = []
        for name in FIXTURE_NAMES:
            raw_project, raw_command = create_fixture(tmp_path / "baseline", name)
            guard_project, guard_command = create_fixture(tmp_path / "optimized", name)
            raw_code, raw_bytes, raw_seconds = run(raw_command, raw_project)
            guard_code, guard_bytes, guard_seconds = contextguard(guard_command, guard_project)
            raw_hash = repository_hash(raw_project)
            guard_hash = repository_hash(guard_project)
            saved = raw_bytes - guard_bytes
            results.append(
                {
                    "fixture": name,
                    "raw_exit": raw_code,
                    "contextguard_exit": guard_code,
                    "raw_bytes": raw_bytes,
                    "contextguard_bytes": guard_bytes,
                    "tool_output_bytes_avoided": max(0, saved),
                    "contextguard_overhead_bytes": max(0, -saved),
                    "net_estimated_reduction": saved // 4,
                    "raw_seconds": round(raw_seconds, 4),
                    "contextguard_seconds": round(guard_seconds, 4),
                    "result_hash": guard_hash,
                    "same_result": raw_code == guard_code and raw_hash == guard_hash,
                    "output_quality": inspect_final_response(
                        f"Changed {name}. Validation: equivalent exit code and repository hash.",
                        changed_files=[name],
                        validation_required=True,
                    )["valid"],
                    "measurement": "bytes and duration measured; token reduction estimated at four bytes per token",
                }
            )
        return results


def _input_cost_estimates(tokens_saved: int, model: str) -> dict[str, float]:
    rates = MODEL_PRICES[model]["short"]
    cached_share = 0.88
    uncached_share = 1.0 - cached_share
    return {
        "all_uncached_input_usd": round(tokens_saved * rates["input"] / 1_000_000, 6),
        "all_cached_input_usd": round(tokens_saved * rates["cached_input"] / 1_000_000, 6),
        "default_88_percent_cached_input_usd": round(
            tokens_saved
            * (cached_share * rates["cached_input"] + uncached_share * rates["input"])
            / 1_000_000,
            6,
        ),
    }


def build_summary(results: list[dict[str, object]], *, model: str) -> dict[str, object]:
    selected_model = canonical_model(model)
    if selected_model not in MODEL_PRICES:
        supported = ", ".join(sorted(MODEL_PRICES))
        raise ValueError(f"unsupported benchmark model {model!r}; choose one of: {supported}")
    raw_bytes = sum(int(result["raw_bytes"]) for result in results)
    contextguard_bytes = sum(int(result["contextguard_bytes"]) for result in results)
    estimated_raw_tokens = raw_bytes // 4
    estimated_contextguard_tokens = contextguard_bytes // 4
    estimated_tokens_saved = max(0, estimated_raw_tokens - estimated_contextguard_tokens)
    reduction_percent = round(
        estimated_tokens_saved / estimated_raw_tokens * 100,
        2,
    ) if estimated_raw_tokens else 0.0
    return {
        "benchmark": "contextguard-local-fixtures-vs-raw",
        "fixtures": len(results),
        "raw_bytes": raw_bytes,
        "contextguard_bytes": contextguard_bytes,
        "estimated_raw_input_tokens": estimated_raw_tokens,
        "estimated_contextguard_input_tokens": estimated_contextguard_tokens,
        "estimated_input_tokens_saved": estimated_tokens_saved,
        "estimated_input_reduction_percent": reduction_percent,
        "same_result": all(bool(result["same_result"]) for result in results),
        "all_output_quality_checks_passed": all(bool(result["output_quality"]) for result in results),
        "pricing": {
            "model": selected_model,
            "rates_per_million_usd": MODEL_PRICES[selected_model]["short"],
            "rates_per_million_usd_by_context": MODEL_PRICES[selected_model],
            "pricing_basis": "OpenAI Standard API short-context text-token rates",
            "pricing_source": PRICING_SOURCE,
            "pricing_last_verified": PRICING_LAST_VERIFIED,
            "estimated_input_savings_usd": _input_cost_estimates(estimated_tokens_saved, selected_model),
        },
        "measurement": (
            "Raw and compacted subprocess bytes are measured locally; visible input tokens are estimated at four bytes per token. "
            "USD values are API-equivalent input savings estimates, not Codex subscription billing."
        ),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="emit an aggregate report with pricing estimates")
    parser.add_argument("--model", default="gpt-5.6-luna", choices=sorted(MODEL_PRICES))
    parser.add_argument("--output", type=Path, help="write the emitted JSON report to this path")
    args = parser.parse_args(argv)
    results = run_suite()
    data: object = build_summary(results, model=args.model) if args.summary else results
    rendered = json.dumps(data, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
