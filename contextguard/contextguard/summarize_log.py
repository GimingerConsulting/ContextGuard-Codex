from __future__ import annotations

import re
from collections import Counter, deque
from pathlib import Path


_SEVERITY = re.compile(r"\b(DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b", re.I)
_ERROR = re.compile(r"\b(error|failed|failure|exception|critical|fatal)\b", re.I)
_VARIABLE = re.compile(
    r"\b(?:[0-9a-f]{8}-[0-9a-f-]{27,}|\d{1,3}(?:\.\d{1,3}){3}|\d+(?:\.\d+)?)\b|\b\w+=\S+",
    re.I,
)


def summarize(path: Path, limit: int = 10) -> dict:
    line_count = 0
    severity_counts: Counter[str] = Counter()
    error_signatures: list[str] = []
    seen: set[str] = set()
    tail: deque[str] = deque(maxlen=limit)
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line_count += 1
            line = raw_line.rstrip("\r\n")
            tail.append(line[:500])
            severity = _SEVERITY.search(line)
            if severity:
                severity_counts[severity.group(1).upper().replace("WARNING", "WARN")] += 1
            if _ERROR.search(line):
                signature = _VARIABLE.sub("<var>", line)[:500]
                if signature not in seen and len(error_signatures) < limit:
                    seen.add(signature)
                    error_signatures.append(signature)
    return {
        "file": path.as_posix(),
        "size": path.stat().st_size,
        "line_count": line_count,
        "severity_counts": dict(severity_counts),
        "error_signatures": error_signatures,
        "tail": list(tail),
    }
