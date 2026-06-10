import subprocess
import sys
import json
from pathlib import Path

from benchmarks.output_ab import compare_output


ROOT = Path(__file__).resolve().parents[1]


def test_compare_output_requires_exact_archived_raw_output(tmp_path):
    raw = "FAILED tests/test_demo.py::test_value - AssertionError\n1 failed in 0.01s\n" * 100
    result = compare_output(raw, tmp_path, timing_samples=1)
    assert result["equivalent_information"] is True
    assert result["archived_output_sha256"] == result["raw_output_sha256"]
    assert result["contextguard_visible_tokens"] < result["raw_visible_tokens"]
    assert result["token_reduction_percent"] > 0


def test_output_ab_runs_as_a_standalone_script(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "benchmarks/output_ab.py"), "--timing-samples", "1", "--output", str(tmp_path / "result.json")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "result.json").exists()
    stored = json.loads((tmp_path / "result.json").read_text())
    assert "visible_output" not in stored
    assert "full_output:" not in stored["visible_summary"]
