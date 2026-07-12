from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import state_dir
from .database import connect, increment
from .output_compactor import compact_output, finalize_evidence
from .adaptive_capture import should_compact as adaptive_should_compact
from .history_pack import record_archive_metadata
from .budget_enforcer import evaluate_budget, render_budget_feedback
from .evidence_expand import build_evidence_expand_directive
from .ledger import record_ledger
from .optimization_advisor import analyze_command, analyze_completed_command, record_command
from .session_state import record_evidence


NOISY_MEDIUM_BYTES = 2048
SMALL_PASSTHROUGH_BYTES = 4096
DEFAULT_MAX_RETAINED_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 30 * 60
DEFAULT_MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_ARCHIVE_COMMANDS = 200


def _positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _drain_stream(stream, path: Path, limit: int, result: dict[str, object]) -> None:
    head_limit = limit // 2
    tail_limit = limit - head_limit
    head = bytearray()
    tail = bytearray()
    seen = 0
    while True:
        chunk = stream.read(65_536)
        if not chunk:
            break
        seen += len(chunk)
        remaining = chunk
        if len(head) < head_limit:
            take = min(head_limit - len(head), len(remaining))
            head.extend(remaining[:take])
            remaining = remaining[take:]
        if remaining:
            tail.extend(remaining)
            if len(tail) > tail_limit:
                del tail[:-tail_limit]
    truncated = seen > limit
    marker = f"\n... ContextGuard truncated {seen - limit} archived bytes ...\n".encode() if truncated else b""
    payload = bytes(head) + marker + bytes(tail)
    path.write_bytes(payload)
    result.update({"bytes": seen, "retained": len(payload), "truncated": truncated, "content": payload})


def _run_bounded(argv: list[str], root: Path, stdout_path: Path, stderr_path: Path) -> tuple[int, dict, dict, bool]:
    limit = _positive_env_int("CONTEXTGUARD_MAX_RETAINED_BYTES", DEFAULT_MAX_RETAINED_BYTES)
    timeout = _positive_env_int("CONTEXTGUARD_CAPTURE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    proc = subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_result: dict[str, object] = {}
    stderr_result: dict[str, object] = {}
    stdout_thread = threading.Thread(target=_drain_stream, args=(proc.stdout, stdout_path, limit, stdout_result), daemon=True)
    stderr_thread = threading.Thread(target=_drain_stream, args=(proc.stderr, stderr_path, limit, stderr_result), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        proc.wait()
    stdout_thread.join()
    stderr_thread.join()
    return (124 if timed_out else proc.returncode), stdout_result, stderr_result, timed_out


def _prune_archives(tmp_dir: Path, *, keep: set[Path] | None = None) -> int:
    keep = {path.resolve() for path in (keep or set())}
    byte_limit = _positive_env_int("CONTEXTGUARD_MAX_ARCHIVE_BYTES", DEFAULT_MAX_ARCHIVE_BYTES)
    command_limit = _positive_env_int("CONTEXTGUARD_MAX_ARCHIVE_COMMANDS", DEFAULT_MAX_ARCHIVE_COMMANDS)
    groups: dict[str, list[Path]] = {}
    for path in tmp_dir.glob("command-*"):
        key = path.name.split(".stdout.txt", 1)[0].split(".stderr.txt", 1)[0].split(".summary.json", 1)[0]
        groups.setdefault(key, []).append(path)
    ordered = sorted(groups.values(), key=lambda items: max(item.stat().st_mtime for item in items), reverse=True)
    retained_bytes = 0
    removed = 0
    for index, paths in enumerate(ordered):
        size = sum(path.stat().st_size for path in paths if path.exists())
        must_keep = any(path.resolve() in keep for path in paths)
        allowed = index < command_limit and retained_bytes + size <= byte_limit
        if must_keep or allowed:
            retained_bytes += size
            continue
        for path in paths:
            try:
                path.unlink()
                removed += 1
            except FileNotFoundError:
                pass
    return removed


def _is_noisy_medium_output(summary: dict) -> bool:
    raw_bytes = int(summary.get("raw_bytes", 0))
    if raw_bytes < NOISY_MEDIUM_BYTES:
        return False
    if summary.get("errors"):
        return True
    return int(summary.get("line_count", 0)) > 50


def _render_summary(argv: list[str], summary: dict) -> str:
    archive = summary.get("display_summary_path", summary["summary_path"])
    repeated = summary.get("repeated_evidence")
    if repeated and repeated.get("repeated"):
        rendered = (
            f"ContextGuard repeated evidence ({repeated['occurrences']}); reuse prior diagnosis.\n"
        )
        if summary.get("test_summary"):
            rendered += f"tests: {summary['test_summary']}\n"
        if summary.get("failed_tests"):
            rendered += "failed_tests:\n" + "\n".join(
                f"- {name}" for name in summary["failed_tests"][:3]
            ) + "\n"
        return rendered + f"archive: {archive}\n"
    outcome = (summary.get("evidence") or {}).get("outcome")
    if summary.get("exit_code") == 0 and outcome == "passed":
        return f"ContextGuard PASS | {summary['test_summary']} | archive: {archive}\n"
    if (
        summary.get("exit_code") == 0
        and not summary.get("errors")
        and not summary.get("warnings")
        and not summary.get("signal_lines")
    ):
        return f"ContextGuard OK | {summary['raw_bytes']}B archived | archive: {archive}\n"
    lines = [
        "ContextGuard capture summary",
        f"exit_code: {summary['exit_code']}",
        f"duration: {summary['duration_ms']} ms",
        f"raw_bytes: {summary['raw_bytes']}",
    ]
    if summary.get("archive_truncated"):
        lines.append("archive_truncated: true (bounded head/tail retained)")
    if summary.get("test_summary"):
        lines.append(f"tests: {summary['test_summary']}")
    for title, key in (("unique_errors", "errors"), ("unique_warnings", "warnings"), ("failed_tests", "failed_tests")):
        values = summary.get(key) or []
        if values:
            lines.append(f"{title}:")
            lines.extend(f"- {value}" for value in values)
    locations = (summary.get("evidence") or {}).get("locations") or []
    if locations:
        lines.append("locations:")
        lines.extend(f"- {value}" for value in locations)
    if summary.get("stack_traces"):
        lines.append("stack_trace:")
        lines.append(summary["stack_traces"][0])
    signal_lines = summary.get("signal_lines") or []
    if signal_lines:
        lines.append("signal:")
        lines.extend(f"- {line}" for line in signal_lines[:16])
    escalation = summary.get("escalation") or {}
    if escalation.get("required"):
        lines.append(f"escalation: {escalation['reason']}")
        lines.append(f"next_action: {escalation['action']}")
        samples = summary.get("summary_lines") or []
        if samples:
            lines.append("evidence_sample:")
            lines.extend(f"- {line}" for line in samples[:2])
    expand_directive = summary.get("expand_directive")
    if expand_directive:
        lines.append(expand_directive)
    lines.append(f"archive: {archive}")
    return "\n".join(lines) + "\n"


def capture(root: Path, argv: list[str]) -> int:
    tmp_dir = state_dir(root) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    command = shlex.join(argv)
    budget = evaluate_budget(root, command)
    if budget.action == "deny":
        print(render_budget_feedback(budget), file=sys.stderr)
        return 2
    if budget.action == "advise":
        print(render_budget_feedback(budget), file=sys.stderr)
    advice = analyze_command(root, command)
    started = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = tmp_dir / f"command-{stamp}-{int(started * 1000)}"
    stdout_path = base.with_suffix(".stdout.txt")
    stderr_path = base.with_suffix(".stderr.txt")
    summary_path = base.with_suffix(".summary.json")
    exit_code, stdout_result, stderr_result, timed_out = _run_bounded(
        argv, root, stdout_path, stderr_path
    )
    stdout = bytes(stdout_result.get("content", b"")).decode("utf-8", errors="replace")
    stderr = bytes(stderr_result.get("content", b"")).decode("utf-8", errors="replace")
    if timed_out:
        stderr += f"\nContextGuardError: command timed out after {_positive_env_int('CONTEXTGUARD_CAPTURE_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS)} seconds\n"
    record_command(root, command, succeeded=exit_code == 0)
    advice = advice or analyze_completed_command(root, command)
    duration_ms = int((time.time() - started) * 1000)
    summary = compact_output(stdout, stderr, command=command)
    summary.update(
        {
            "stdout_bytes": int(stdout_result.get("bytes", 0)),
            "stderr_bytes": int(stderr_result.get("bytes", 0)),
            "raw_bytes": int(stdout_result.get("bytes", 0)) + int(stderr_result.get("bytes", 0)),
            "archive_truncated": bool(stdout_result.get("truncated")) or bool(stderr_result.get("truncated")),
            "timed_out": timed_out,
        }
    )
    summary.update(
        {
            "command": argv,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout_path": stdout_path.as_posix(),
            "stderr_path": stderr_path.as_posix(),
            "summary_path": summary_path.as_posix(),
            "display_summary_path": summary_path.relative_to(root).as_posix(),
            "optimization_advice": advice,
        }
    )
    finalize_evidence(summary)
    evidence_block = summary.get("evidence") or {}
    summary["repeated_evidence"] = record_evidence(
        root,
        summary["evidence_fingerprint"],
        summary_path.as_posix(),
        locations=list(evidence_block.get("locations") or []),
        failed_tests=list(evidence_block.get("failed_tests") or []),
    )
    summary["expand_directive"] = build_evidence_expand_directive(root, summary["evidence_fingerprint"])
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    conn = connect(state_dir(root) / "index.sqlite")
    conn.execute(
        "insert into commands(command, exit_code, duration_ms, stdout_bytes, stderr_bytes, output_path) values(?,?,?,?,?,?)",
        (" ".join(argv), exit_code, duration_ms, summary["stdout_bytes"], summary["stderr_bytes"], summary_path.as_posix()),
    )
    increment(conn, "commands_intercepted", 1)
    increment(conn, "raw_output_bytes", summary["stdout_bytes"] + summary["stderr_bytes"])
    raw_bytes = summary["raw_bytes"]
    should_compact = (
        bool(advice)
        or adaptive_should_compact(
            raw_bytes,
            root,
            has_errors=bool(summary.get("errors")),
            line_count=int(summary.get("line_count", 0)),
        )
        or raw_bytes > SMALL_PASSTHROUGH_BYTES
        or _is_noisy_medium_output(summary)
    )
    if should_compact:
        rendered = _render_summary(argv, summary)
        shown_bytes = len(rendered.encode())
    else:
        rendered = ""
        shown_bytes = raw_bytes
        record_ledger(root, "passthrough", bytes_added=raw_bytes, label=command)
    increment(conn, "compact_output_bytes", shown_bytes)
    increment(conn, "estimated_saved_bytes", max(0, raw_bytes - shown_bytes))
    conn.commit()
    if should_compact:
        record_ledger(root, "capture", bytes_saved=max(0, raw_bytes - shown_bytes), label=command)
        record_archive_metadata(
            root,
            archive_path=summary_path.as_posix(),
            fingerprint=summary["evidence_fingerprint"],
            raw_bytes=raw_bytes,
        )
    if not should_compact:
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        _prune_archives(tmp_dir, keep={stdout_path, stderr_path, summary_path})
        return exit_code
    print(rendered, end="")
    _prune_archives(tmp_dir, keep={stdout_path, stderr_path, summary_path})
    return exit_code
