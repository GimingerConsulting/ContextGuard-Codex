import json
from pathlib import Path

from contextguard.config import state_dir
from contextguard.output_retrieval import retrieve_output
from contextguard.session_state import record_output


def _archive(root: Path) -> str:
    archive = state_dir(root) / "tmp"
    archive.mkdir(parents=True)
    stdout_path = archive / "stdout.txt"
    stderr_path = archive / "stderr.txt"
    summary_path = archive / "summary.json"
    stdout_path.write_text("\n".join(f"stdout-{index}" for index in range(1, 61)) + "\n", encoding="utf-8")
    stderr_path.write_text("\n".join(f"ERROR stderr-{index}" for index in range(1, 31)) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps({
        "command": ["demo"],
        "exit_code": 1,
        "raw_bytes": stdout_path.stat().st_size + stderr_path.stat().st_size,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "summary_path": str(summary_path),
        "archive_truncated": False,
    }), encoding="utf-8")
    fingerprint = "a" * 64
    record_output(root, fingerprint, str(summary_path), raw_bytes=summary_path.stat().st_size)
    return f"cg://output/{fingerprint[:12]}"


def test_retrieval_streams_line_ranges_and_bounds_grep_results(tmp_path: Path):
    handle = _archive(tmp_path)

    window = retrieve_output(tmp_path, handle, lines=(2, 3))
    assert window["content"] == [
        "stdout:2:stdout-2",
        "stdout:3:stdout-3",
        "stderr:2:ERROR stderr-2",
        "stderr:3:ERROR stderr-3",
    ]

    matches = retrieve_output(tmp_path, handle, pattern="ERROR")
    assert matches["selection"]["match_count"] == 30
    assert matches["selection"]["returned"] == 20
    assert len(matches["content"]) == 20
