from __future__ import annotations

import json
import re
from pathlib import Path

from .config import state_dir
from .ledger import record_ledger
from .session_state import load_session_state
from .source_inspector import InspectionError, inspect_sources


def _load_summary(summary_path: str) -> dict:
    path = Path(summary_path)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _parse_location(location: str) -> tuple[str, int | None]:
    match = re.match(r"^(.+?):(\d+)$", location)
    if match:
        return match.group(1), int(match.group(2))
    return location, None


def build_evidence_expand_directive(root: Path, fingerprint: str) -> str:
    state = load_session_state(root)
    entry = (state.get("evidence") or {}).get(fingerprint)
    if not entry:
        return ""
    summary = _load_summary(str(entry.get("last_summary_path") or entry.get("first_summary_path") or ""))
    evidence = summary.get("evidence") or {}
    locations = list(entry.get("locations") or evidence.get("locations") or [])
    failed_tests = list(entry.get("failed_tests") or evidence.get("failed_tests") or [])
    lines = ["ContextGuard evidence expand:"]
    if failed_tests:
        lines.append("failed_tests: " + ", ".join(failed_tests[:3]))
    for location in locations[:3]:
        path, line_number = _parse_location(location)
        if line_number:
            lines.append(
                f"inspect next: `.contextguard/bin/contextguard inspect {path} --start-line {max(1, line_number - 20)} --end-line {line_number + 20}`"
            )
        else:
            lines.append(f"expand next: `.contextguard/bin/contextguard expand {path}`")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def expand_from_evidence(root: Path, fingerprint: str) -> dict[str, object]:
    state = load_session_state(root)
    entry = (state.get("evidence") or {}).get(fingerprint)
    if not entry:
        return {"ok": False, "error": "missing_evidence"}
    summary = _load_summary(str(entry.get("last_summary_path") or entry.get("first_summary_path") or ""))
    locations = list(entry.get("locations") or (summary.get("evidence") or {}).get("locations") or [])
    if not locations:
        return {"ok": False, "error": "no_locations"}
    path, line_number = _parse_location(locations[0])
    start = max(1, line_number - 20) if line_number else 1
    end = line_number + 20 if line_number else 200
    try:
        inspected = inspect_sources(root, [path], start_line=start, end_line=end)
    except InspectionError as exc:
        return {"ok": False, "error": exc.code, "message": str(exc), "path": path}
    entry_result = inspected["files"][0]
    expanded = {
        "ok": True,
        "path": entry_result["path"],
        "sha256": entry_result["fingerprint"],
        "bytes": entry_result["bytes"],
        "window": {
            "start_line": entry_result["selection"]["start_line"],
            "end_line": entry_result["selection"]["end_line"],
            "content": entry_result["content"],
        },
    }
    record_ledger(root, "expand", bytes_added=len(str(expanded).encode()), label=f"evidence:{fingerprint[:8]}")
    return {"ok": True, "fingerprint": fingerprint, "location": locations[0], "result": expanded}


def list_evidence_entries(root: Path) -> list[dict[str, object]]:
    state = load_session_state(root)
    entries = []
    for fingerprint, entry in (state.get("evidence") or {}).items():
        entries.append(
            {
                "fingerprint": fingerprint,
                "occurrences": entry.get("occurrences", 1),
                "locations": entry.get("locations", []),
                "failed_tests": entry.get("failed_tests", []),
            }
        )
    return entries


def write_evidence_index(root: Path) -> Path:
    path = state_dir(root) / "sessions" / "evidence_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entries": list_evidence_entries(root)}, indent=2) + "\n", encoding="utf-8")
    return path
