from __future__ import annotations

from .utils import extract_error_lines


def _clip(line: str, limit: int = 500) -> str:
    return line if len(line) <= limit else line[:limit] + " ... [truncated]"


def compact_output(stdout: str, stderr: str = "", *, limit: int = 24) -> dict:
    combined = "\n".join(part for part in (stdout, stderr) if part)
    lines = combined.splitlines()
    errors = extract_error_lines(combined)
    head = [_clip(line) for line in lines[: min(8, len(lines))]]
    tail = [_clip(line) for line in lines[-8:]] if len(lines) > 8 else []
    selected = []
    for line in head + errors + tail:
        if line not in selected:
            selected.append(line)
        if len(selected) >= limit:
            break
    summary_text = "\n".join(selected)
    raw_bytes = len(stdout.encode()) + len(stderr.encode())
    return {
        "line_count": len(lines),
        "stdout_bytes": len(stdout.encode()),
        "stderr_bytes": len(stderr.encode()),
        "raw_bytes": raw_bytes,
        "compact_bytes": len(summary_text.encode()),
        "errors": [_clip(line) for line in errors[:10]],
        "summary_lines": selected,
    }
