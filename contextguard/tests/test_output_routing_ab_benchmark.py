import json
import subprocess
import sys
from pathlib import Path

from benchmarks.output_routing_ab import run_benchmark


ROOT = Path(__file__).resolve().parents[1]


def test_output_routing_ab_preserves_archives_and_saves_tokens(tmp_path: Path):
    result = run_benchmark(tmp_path / "result.json")

    assert result["valid"] is True
    assert result["contextguard_visible_tokens"] < result["raw_visible_tokens"]
    assert result["token_reduction_percent"] > 90
    assert result["new_route_baseline"]["improvement_percent"] > 90
    assert {case["output_kind"] for case in result["cases"]} >= {"log", "json"}


def test_output_routing_ab_runs_standalone(tmp_path: Path):
    output = tmp_path / "standalone.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "benchmarks" / "output_routing_ab.py"), "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["valid"] is True
    assert all("first_visible" not in case for case in stored["cases"])
