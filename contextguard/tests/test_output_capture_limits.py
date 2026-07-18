from pathlib import Path

from contextguard.output_capture import _prune_archives, _render_summary, _run_bounded


def test_run_bounded_archives_exact_output_and_bounds_analysis_sample(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CONTEXTGUARD_MAX_RETAINED_BYTES", "1024")
    stdout_path = tmp_path / "stdout.txt"
    stderr_path = tmp_path / "stderr.txt"
    body_size = 2 * 1024 * 1024 + 123
    code = f"import sys; print('HEAD'); print('x' * {body_size}); print('TAIL')"

    exit_code, stdout, stderr, timed_out = _run_bounded(
        ["python3", "-c", code], tmp_path, stdout_path, stderr_path
    )

    archived = stdout_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert timed_out is False
    assert stdout["bytes"] > 2 * 1024 * 1024
    assert stdout["truncated"] is True
    assert archived == "HEAD\n" + "x" * body_size + "\nTAIL\n"
    assert stdout["retained"] <= 1100
    assert b"HEAD" in stdout["content"]
    assert b"TAIL" in stdout["content"]
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
        "content_fingerprint": "a" * 64,
        "test_summary": "210 passed in 88.85s",
        "evidence": {"outcome": "passed"},
    })

    assert rendered.startswith("ContextGuard PASS | 210 passed")
    assert "reuse until relevant code changes" in rendered
    assert "handle:" not in rendered
    assert len(rendered.encode()) < 140


def test_repeated_exact_output_uses_compact_reversible_reference():
    rendered = _render_summary([], {
        "summary_path": "/tmp/result.json",
        "display_summary_path": ".contextguard/tmp/result.json",
        "content_fingerprint": "abc123def456" + "0" * 52,
        "repeated_output": {"repeated": True, "reference": "abc123def456", "occurrences": 3},
    })

    assert rendered == (
        "ContextGuard REUSE | ref:abc123def456 x3 unchanged; no action needed\n"
    )


def test_diagnostic_failure_does_not_advertise_an_archive_roundtrip():
    rendered = _render_summary([], {
        "summary_path": "/tmp/result.json",
        "display_summary_path": ".contextguard/tmp/result.json",
        "content_fingerprint": "b" * 64,
        "exit_code": 1,
        "duration_ms": 2,
        "raw_bytes": 5000,
        "errors": ["ValueError: broken"],
        "warnings": [],
        "failed_tests": ["tests/test_api.py::test_case"],
        "evidence": {"outcome": "failed", "locations": ["api.py:20"]},
        "escalation": {"required": False},
    })

    assert "ValueError: broken" in rendered
    assert "api.py:20" in rendered
    assert "handle:" not in rendered
    assert "archive:" not in rendered


def test_missing_failure_diagnostic_exposes_exactly_one_expansion_path():
    rendered = _render_summary([], {
        "summary_path": "/tmp/result.json",
        "display_summary_path": ".contextguard/tmp/result.json",
        "content_fingerprint": "c" * 64,
        "exit_code": 1,
        "duration_ms": 2,
        "raw_bytes": 5000,
        "errors": [],
        "warnings": [],
        "evidence": {"outcome": "failed", "locations": []},
        "escalation": {"required": True, "reason": "failed_without_diagnostic", "action": "expand once"},
        "expand_directive": "expand one bounded slice",
    })

    assert rendered.count("handle:") == 1
    assert rendered.count("archive:") == 1
    assert "expand one bounded slice" in rendered
