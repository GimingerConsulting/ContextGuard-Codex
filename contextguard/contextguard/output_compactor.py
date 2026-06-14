from __future__ import annotations

import hashlib
import json
import re


def _clip(line: str, limit: int = 500) -> str:
    return line if len(line) <= limit else line[:limit] + " ... [truncated]"


def _signature(line: str) -> str:
    return re.sub(r"\b\d+(?:\.\d+)?\b", "N", line.strip().lower())[:300]


def _unique_matching(lines: list[str], pattern: re.Pattern[str], limit: int = 20) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for line in lines:
        compact = line.strip()
        if not compact or not pattern.search(compact):
            continue
        signature = _signature(compact)
        if signature in seen:
            continue
        seen.add(signature)
        selected.append(_clip(compact))
        if len(selected) >= limit:
            break
    return selected


def _locations(lines: list[str], limit: int = 8) -> list[str]:
    locations: list[str] = []
    patterns = (
        re.compile(r'File ["\']([^"\']+)["\'], line (\d+)'),
        re.compile(r"(?<![\w/.-])([\w./-]+\.[A-Za-z0-9]+):(\d+)"),
    )
    for line in lines:
        for pattern in patterns:
            for path, line_number in pattern.findall(line):
                location = f"{path}:{line_number}"
                if location not in locations:
                    locations.append(location)
                if len(locations) >= limit:
                    return locations
    return locations


def finalize_evidence(summary: dict) -> dict:
    evidence = summary.get("evidence") or {}
    exit_code = summary.get("exit_code")
    diagnostic = bool(
        evidence.get("failed_tests")
        or evidence.get("errors")
        or evidence.get("locations")
        or summary.get("stack_traces")
    )
    failed = exit_code not in (None, 0) or evidence.get("outcome") == "failed"
    if failed and not diagnostic:
        summary["confidence"] = "low"
        summary["escalation"] = {
            "required": True,
            "reason": "failed_without_diagnostic",
            "action": "Inspect a bounded slice of the archived stdout/stderr.",
        }
        summary["next_action"] = summary["escalation"]["action"]
    else:
        summary["confidence"] = "high" if diagnostic or evidence.get("outcome") in {"passed", "failed"} else "medium"
        summary["escalation"] = {"required": False, "reason": None, "action": None}
        if evidence.get("outcome") == "passed":
            summary["next_action"] = "Reuse this passing result until relevant code changes."
        elif evidence.get("failed_tests") and evidence.get("locations"):
            summary["next_action"] = "Inspect the listed location, patch, then rerun only the failed test."
        elif evidence.get("failed_tests"):
            summary["next_action"] = "Rerun one failed test with a short traceback, then patch."
        elif failed:
            summary["next_action"] = "Act on the unique diagnostic, then rerun the smallest relevant check."
        else:
            summary["next_action"] = None
    return summary


def compact_output(stdout: str, stderr: str = "", *, limit: int = 24) -> dict:
    combined = "\n".join(part for part in (stdout, stderr) if part)
    lines = combined.splitlines()
    warnings = _unique_matching(lines, re.compile(r"\bwarning\b", re.I), 10)
    errors = _unique_matching(
        lines,
        re.compile(r"\b(error|failed|failure|exception)\b|^[A-Za-z_][A-Za-z0-9_.]*Error:", re.I),
        20,
    )
    warning_signatures = {_signature(line) for line in warnings}
    errors = [line for line in errors if _signature(line) not in warning_signatures]
    failed_tests = []
    for line in lines:
        match = re.match(r"\s*FAILED\s+([^\s]+)", line)
        if match and match.group(1) not in failed_tests:
            failed_tests.append(match.group(1))
    test_summary = next(
        (line.strip() for line in reversed(lines) if re.search(r"\b\d+\s+(?:failed|passed|error|errors)\b", line, re.I)),
        None,
    )
    deduped_errors = []
    seen_failed_tests: set[str] = set()
    for line in errors:
        failed = re.match(r"FAILED\s+([^\s]+)", line, re.I)
        if failed:
            if failed.group(1) in seen_failed_tests:
                continue
            seen_failed_tests.add(failed.group(1))
        if test_summary and line == test_summary:
            continue
        deduped_errors.append(line)
    errors = deduped_errors
    stack_traces = []
    for index, line in enumerate(lines):
        if "Traceback (most recent call last)" in line:
            stack_traces.append("\n".join(_clip(item) for item in lines[index : index + 5]))
            break
    head = [_clip(line) for line in lines[: min(8, len(lines))]]
    tail = [_clip(line) for line in lines[-8:]] if len(lines) > 8 else []
    selected = []
    for line in errors + warnings + head + tail:
        if line not in selected:
            selected.append(line)
        if len(selected) >= limit:
            break
    summary_text = "\n".join(selected)
    raw_bytes = len(stdout.encode()) + len(stderr.encode())
    outcome = "unknown"
    if test_summary:
        outcome = "failed" if re.search(r"\b(?:failed|error|errors)\b", test_summary, re.I) else "passed"
    elif errors:
        outcome = "failed"
    evidence = {
        "outcome": outcome,
        "test_summary": test_summary,
        "failed_tests": failed_tests[:20],
        "errors": [_clip(line) for line in errors[:10]],
        "warnings": warnings,
        "locations": _locations(lines),
    }
    fingerprint_payload = {
        key: value
        for key, value in evidence.items()
        if value not in (None, [], "", "unknown")
    }
    fingerprint_payload["summary_lines"] = selected
    result = {
        "line_count": len(lines),
        "stdout_bytes": len(stdout.encode()),
        "stderr_bytes": len(stderr.encode()),
        "raw_bytes": raw_bytes,
        "compact_bytes": len(summary_text.encode()),
        "errors": [_clip(line) for line in errors[:10]],
        "warnings": warnings,
        "failed_tests": failed_tests[:20],
        "test_summary": test_summary,
        "stack_traces": stack_traces,
        "summary_lines": selected,
        "evidence": evidence,
        "evidence_fingerprint": hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True).encode()
        ).hexdigest(),
    }
    return finalize_evidence(result)
