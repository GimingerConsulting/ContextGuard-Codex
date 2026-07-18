from __future__ import annotations

import json
import re
from pathlib import Path

from .config import state_dir
from .session_state import load_session_state


HANDLE_RE = re.compile(r"^(?:cg://output/)?([0-9a-f]{12,64})$")
MAX_WINDOW_LINES = 200
MAX_MATCHES = 20


def _resolve_output(root: Path, handle: str) -> tuple[str, dict, dict]:
    match = HANDLE_RE.fullmatch(handle.strip().lower())
    if not match:
        raise ValueError("invalid output handle")
    prefix = match.group(1)
    outputs = load_session_state(root).get("outputs") or {}
    matches = [(fingerprint, entry) for fingerprint, entry in outputs.items() if fingerprint.startswith(prefix)]
    if not matches:
        raise ValueError("output handle not found in the current session")
    if len(matches) > 1:
        raise ValueError("ambiguous output handle; provide more hash characters")
    fingerprint, entry = matches[0]
    summary_path = Path(str(entry.get("last_summary_path") or entry.get("first_summary_path") or "")).resolve()
    try:
        summary_path.relative_to(state_dir(root).resolve())
    except ValueError as exc:
        raise ValueError("output archive escapes project state") from exc
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("output archive is unavailable") from exc
    return fingerprint, entry, summary


def _stream_text(root: Path, summary: dict, key: str) -> str:
    path = Path(str(summary.get(f"{key}_path") or "")).resolve()
    try:
        path.relative_to(state_dir(root).resolve())
    except ValueError as exc:
        raise ValueError("output stream escapes project state") from exc
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValueError("output stream is unavailable") from exc


def retrieve_output(
    root: Path,
    handle: str,
    *,
    lines: tuple[int, int] | None = None,
    pattern: str | None = None,
    stream: str = "both",
) -> dict[str, object]:
    fingerprint, entry, summary = _resolve_output(root, handle)
    result: dict[str, object] = {
        "ok": True,
        "handle": f"cg://output/{fingerprint[:12]}",
        "command": summary.get("command", []),
        "exit_code": summary.get("exit_code"),
        "raw_bytes": summary.get("raw_bytes", entry.get("raw_bytes", 0)),
        "archive_truncated": bool(summary.get("archive_truncated")),
        "available_streams": ["stdout", "stderr"],
    }
    if lines is None and pattern is None:
        return result

    selected_streams = ("stdout", "stderr") if stream == "both" else (stream,)
    content: list[tuple[str, int, str]] = []
    for stream_name in selected_streams:
        for number, text in enumerate(_stream_text(root, summary, stream_name).splitlines(), 1):
            content.append((stream_name, number, text))

    if lines is not None:
        start, end = lines
        if start < 1 or end < start or end - start + 1 > MAX_WINDOW_LINES:
            raise ValueError(f"line range must contain 1-{MAX_WINDOW_LINES} lines")
        result["selection"] = {"mode": "lines", "start": start, "end": end, "stream": stream}
        result["content"] = [
            f"{stream_name}:{number}:{text}"
            for stream_name, number, text in content
            if start <= number <= end
        ]
        return result

    if pattern is None or not pattern or len(pattern) > 120:
        raise ValueError("grep pattern must contain 1-120 characters")
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"invalid grep pattern: {exc}") from exc
    matches = [
        f"{stream_name}:{number}:{text}"
        for stream_name, number, text in content
        if regex.search(text)
    ]
    result["selection"] = {
        "mode": "grep",
        "pattern": pattern,
        "stream": stream,
        "match_count": len(matches),
        "returned": min(len(matches), MAX_MATCHES),
    }
    result["content"] = matches[:MAX_MATCHES]
    return result
