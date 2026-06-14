from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import state_dir
from .database import connect, increment
from .output_compactor import compact_output, finalize_evidence
from .optimization_advisor import analyze_command, analyze_completed_command, record_command
from .session_state import record_evidence


NOISY_MEDIUM_BYTES = 2048
SMALL_PASSTHROUGH_BYTES = 4096


def _is_noisy_medium_output(summary: dict) -> bool:
    raw_bytes = int(summary.get("raw_bytes", 0))
    if raw_bytes < NOISY_MEDIUM_BYTES:
        return False
    if summary.get("errors"):
        return True
    return int(summary.get("line_count", 0)) > 50


def _render_summary(argv: list[str], summary: dict) -> str:
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
        if summary.get("optimization_advice"):
            rendered += f"optimization_advice: {summary['optimization_advice']}\n"
        return rendered + f"full_output: {summary.get('display_summary_path', summary['summary_path'])}\n"
    lines = [
        "ContextGuard capture summary",
        f"exit_code: {summary['exit_code']}",
        f"duration: {summary['duration_ms']} ms",
        f"raw_bytes: {summary['raw_bytes']}",
    ]
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
    if summary.get("optimization_advice"):
        lines.append(f"optimization_advice: {summary['optimization_advice']}")
    escalation = summary.get("escalation") or {}
    if escalation.get("required"):
        lines.append(f"escalation: {escalation['reason']}")
        lines.append(f"next_action: {escalation['action']}")
        samples = summary.get("summary_lines") or []
        if samples:
            lines.append("evidence_sample:")
            lines.extend(f"- {line}" for line in samples[:2])
    lines.append(f"full_output: {summary.get('display_summary_path', summary['summary_path'])}")
    return "\n".join(lines) + "\n"


def capture(root: Path, argv: list[str]) -> int:
    tmp_dir = state_dir(root) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    command = shlex.join(argv)
    advice = analyze_command(root, command)
    started = time.time()
    proc = subprocess.run(argv, cwd=root, text=True, capture_output=True)
    record_command(root, command, succeeded=proc.returncode == 0)
    advice = advice or analyze_completed_command(root, command)
    duration_ms = int((time.time() - started) * 1000)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = tmp_dir / f"command-{stamp}-{int(started * 1000)}"
    stdout_path = base.with_suffix(".stdout.txt")
    stderr_path = base.with_suffix(".stderr.txt")
    summary_path = base.with_suffix(".summary.json")
    stdout_path.write_text(proc.stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(proc.stderr, encoding="utf-8", errors="replace")
    summary = compact_output(proc.stdout, proc.stderr)
    summary.update(
        {
            "command": argv,
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "stdout_path": stdout_path.as_posix(),
            "stderr_path": stderr_path.as_posix(),
            "summary_path": summary_path.as_posix(),
            "display_summary_path": summary_path.relative_to(root).as_posix(),
            "optimization_advice": advice,
        }
    )
    finalize_evidence(summary)
    summary["repeated_evidence"] = record_evidence(
        root,
        summary["evidence_fingerprint"],
        summary_path.as_posix(),
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    conn = connect(state_dir(root) / "index.sqlite")
    conn.execute(
        "insert into commands(command, exit_code, duration_ms, stdout_bytes, stderr_bytes, output_path) values(?,?,?,?,?,?)",
        (" ".join(argv), proc.returncode, duration_ms, summary["stdout_bytes"], summary["stderr_bytes"], summary_path.as_posix()),
    )
    increment(conn, "commands_intercepted", 1)
    increment(conn, "raw_output_bytes", summary["stdout_bytes"] + summary["stderr_bytes"])
    raw_bytes = summary["raw_bytes"]
    should_compact = bool(advice) or raw_bytes > SMALL_PASSTHROUGH_BYTES or _is_noisy_medium_output(summary)
    if should_compact:
        rendered = _render_summary(argv, summary)
        shown_bytes = len(rendered.encode())
    else:
        shown_bytes = raw_bytes
    increment(conn, "compact_output_bytes", shown_bytes)
    increment(conn, "estimated_saved_bytes", max(0, raw_bytes - shown_bytes))
    conn.commit()
    if not should_compact:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        return proc.returncode
    print(rendered, end="")
    return proc.returncode
