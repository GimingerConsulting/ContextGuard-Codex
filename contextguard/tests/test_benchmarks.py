import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_harness_runs():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "benchmarks" / "run_benchmarks.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert len(payload) >= 10
    assert all(item["raw_exit"] == item["contextguard_exit"] for item in payload)
    assert all(item["same_result"] for item in payload)
    assert all(item["output_quality"] for item in payload)
    assert all("result_hash" in item for item in payload)
    assert all("net_estimated_reduction" in item for item in payload)


def test_benchmark_cli_emits_aggregate_pricing_summary():
    proc = subprocess.run(
        [sys.executable, "-m", "contextguard.cli", "benchmark", "--model", "gpt-6-astra"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["same_result"] is True
    assert payload["estimated_input_tokens_saved"] > 0
    assert payload["pricing"]["model"] == "gpt-6-astra"
    assert payload["pricing"]["rates_per_million_usd"]["input"] == 10.0
    assert payload["pricing"]["rates_per_million_usd_by_context"]["long"]["output"] == 75.0
    assert payload["pricing"]["pricing_source"].startswith("https://developers.openai.com/")
