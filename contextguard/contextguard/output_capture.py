from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import state_dir
from .database import connect, increment
from .output_compactor import compact_output


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
    lines = [
        "ContextGuard capture summary",
        f"command: {' '.join(argv)}",
        f"exit_code: {summary['exit_code']}",
        f"duration_ms: {summary['duration_ms']}",
        f"raw_bytes: {summary['raw_bytes']}",
    ]
    lines.extend(summary["summary_lines"])
    lines.append(f"full_output: {summary['summary_path']}")
    return "\n".join(lines) + "\n"


def capture(root: Path, argv: list[str]) -> int:
    tmp_dir = state_dir(root) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    proc = subprocess.run(argv, cwd=root, text=True, capture_output=True)
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
        }
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
    should_compact = raw_bytes > SMALL_PASSTHROUGH_BYTES or _is_noisy_medium_output(summary)
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
