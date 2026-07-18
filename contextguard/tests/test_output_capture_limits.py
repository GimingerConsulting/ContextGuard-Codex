from pathlib import Path

from contextguard.output_capture import _prune_archives, _render_summary, _run_bounded


def test_run_bounded_retains_head_and_tail(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CONTEXTGUARD_MAX_RETAINED_BYTES", "1024")
    stdout_path = tmp_path / "stdout.txt"
    stderr_path = tmp_path / "stderr.txt"
    code = "import sys; print('HEAD'); print('x' * 4096); print('TAIL')"

    exit_code, stdout, stderr, timed_out = _run_bounded(
        ["python3", "-c", code], tmp_path, stdout_path, stderr_path
    )

    retained = stdout_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert timed_out is False
    assert stdout["bytes"] > 4096
    assert stdout["truncated"] is True
    assert "HEAD" in retained
    assert "TAIL" in retained
    assert stderr["bytes"] == 0


def test_run_bounded_times_out_and_keeps_partial_output(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CONTEXTGUARD_CAPTURE_TIMEOUT_SECONDS", "1")
    stdout_path = tmp_path / "stdout.txt"
    stderr_path = tmp_path / "stderr.txt"
    code = "import time; print('started', flush=True); time.sleep(5)"

    exit_code, stdout, _, timed_out = _run_bounded(
        ["python3", "-c", code], tmp_path, stdout_path, stderr_path
    )

    assert exit_code == 124
    assert timed_out is True
    assert stdout["bytes"] > 0
    assert "started" in stdout_path.read_text(encoding="utf-8")


def test_prune_archives_caps_command_groups(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CONTEXTGUARD_MAX_ARCHIVE_COMMANDS", "2")
    monkeypatch.setenv("CONTEXTGUARD_MAX_ARCHIVE_BYTES", "100000")
    for index in range(4):
        for suffix in ("stdout.txt", "stderr.txt", "summary.json"):
            path = tmp_path / f"command-20260101T00000{index}Z-{index}.{suffix}"
            path.write_text(str(index), encoding="utf-8")
            path.touch()

    removed = _prune_archives(tmp_path)

    assert removed == 6
    assert len(list(tmp_path.glob("command-*"))) == 6


def test_prune_archives_tolerates_a_concurrent_pruner(tmp_path: Path, monkeypatch):
    target = tmp_path / "command-20260101T000000Z-1.stdout.txt"
    target.write_text("output", encoding="utf-8")
    original_stat = Path.stat
    vanished = False

    def racing_stat(path: Path, *args, **kwargs):
        nonlocal vanished
        if path == target and not vanished:
            vanished = True
            target.unlink()
            raise FileNotFoundError(target)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", racing_stat)

    assert _prune_archives(tmp_path) == 0


def test_passing_test_summary_uses_one_line_codec():
    rendered = _render_summary([], {
        "summary_path": "/tmp/result.json",
        "display_summary_path": ".contextguard/tmp/result.json",
        "exit_code": 0,
        "test_summary": "210 passed in 88.85s",
        "evidence": {"outcome": "passed"},
    })

    assert rendered.startswith("ContextGuard PASS | 210 passed")
    assert len(rendered.encode()) < 120


def test_repeated_exact_output_uses_compact_reversible_reference():
    rendered = _render_summary([], {
        "summary_path": "/tmp/result.json",
        "display_summary_path": ".contextguard/tmp/result.json",
        "repeated_output": {"repeated": True, "reference": "abc123def456", "occurrences": 3},
    })

    assert rendered == (
        "ContextGuard ref:abc123def456 x3 unchanged; "
        "archive: .contextguard/tmp/result.json\n"
    )
