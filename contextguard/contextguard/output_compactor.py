from __future__ import annotations

import hashlib
import json
import re
from collections import Counter


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


def _command_signal(lines: list[str], command: str, limit: int = 16) -> list[str]:
    lowered = command.lower().strip()
    if "git diff" in lowered or any(line.startswith("diff --git ") for line in lines):
        signal = [
            line for line in lines
            if line.startswith("diff --git ") or line.startswith("@@ ") or re.search(r"\d+ files? changed", line)
        ]
    elif re.search(r"(?:^|[\s'\"])(?:rg|grep|find|git status)(?:\s|$)", lowered):
        signal = [line for line in lines if line.strip()]
    elif re.search(
        r"(?:^|[\s'\"])(?:cargo|docker|podman|kubectl|terraform|gradle|mvn|gh|go\s+(?:test|build|vet)|npm|pnpm|yarn|bun|ruff|mypy|tsc|eslint|vitest)(?:\s|$)",
        lowered,
    ):
        nonempty = [line for line in lines if line.strip()]
        signal = nonempty[: max(1, limit // 2)]
        if len(nonempty) > limit:
            signal += nonempty[-max(1, limit // 2) :]
    else:
        return []
    clipped = [_clip(line) for line in signal[:limit]]
    if len(signal) > limit:
        clipped.append(f"... {len(signal) - limit} additional signal lines archived")
    return clipped


def _json_signal(combined: str) -> list[str]:
    candidate = combined.strip()
    if not candidate or candidate[:1] not in {"{", "["}:
        return []
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return []
    if isinstance(value, dict):
        keys = [str(key) for key in list(value)[:20]]
        return [
            f"json_object: {len(value)} keys",
            "json_keys: " + ", ".join(keys),
        ]
    if isinstance(value, list):
        signal = [f"json_array: {len(value)} items"]
        object_items = [item for item in value[:20] if isinstance(item, dict)]
        if object_items:
            keys: list[str] = []
            for item in object_items:
                for key in item:
                    rendered = str(key)
                    if rendered not in keys:
                        keys.append(rendered)
                    if len(keys) >= 20:
                        break
            signal.append("item_keys: " + ", ".join(keys))
        return signal
    return [f"json_scalar: {type(value).__name__}"]


def _repeated_line_signal(lines: list[str], limit: int = 6) -> list[str]:
    representatives: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for line in lines:
        compact = line.strip()
        if not compact:
            continue
        signature = _signature(compact)
        representatives.setdefault(signature, compact)
        counts[signature] += 1
    repeated = [item for item in counts.most_common() if item[1] > 1]
    return [
        f"repeated x{count}: {_clip(representatives[signature], 300)}"
        for signature, count in repeated[:limit]
    ]


def _output_kind(command: str, combined: str, lines: list[str], test_summary: str | None) -> str:
    lowered = command.lower()
    if "git diff" in lowered or any(line.startswith("diff --git ") for line in lines):
        return "diff"
    if test_summary or re.search(r"(?:pytest|cargo test|go test|vitest|npm test|pnpm test|yarn test)", lowered):
        return "test"
    if _json_signal(combined):
        return "json"
    if re.search(r"(?:^|[\s'\"])(?:rg|grep|find|git status)(?:\s|$)", lowered):
        return "search"
    if len(lines) > 20 and _repeated_line_signal(lines):
        return "log"
    return "generic"


def _test_outcome(test_summary: str | None) -> str:
    if not test_summary:
        return "unknown"
    failed = re.search(r"\b(\d+)\s+failed\b", test_summary, re.I)
    errors = re.search(r"\b(\d+)\s+errors?\b", test_summary, re.I)
    if (failed and int(failed.group(1)) > 0) or (errors and int(errors.group(1)) > 0):
        return "failed"
    if re.search(r"\b\d+\s+passed\b", test_summary, re.I):
        return "passed"
    return "unknown"


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


def compact_output(stdout: str, stderr: str = "", *, limit: int = 24, command: str = "") -> dict:
    combined = "\n".join(part for part in (stdout, stderr) if part)
    lines = combined.splitlines()
    is_diff = "git diff" in command.lower() or any(line.startswith("diff --git ") for line in lines)
    diagnostic_lines = [line for line in lines if not (is_diff and line.startswith(("+", "-")))]
    warnings = _unique_matching(diagnostic_lines, re.compile(r"warning", re.I), 10)
    errors = _unique_matching(
        diagnostic_lines,
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
    outcome = _test_outcome(test_summary)
    if outcome == "unknown" and errors and not is_diff:
        outcome = "failed"
    output_kind = _output_kind(command, combined, lines, test_summary)
    signal_lines = _command_signal(lines, command)
    if output_kind == "json":
        signal_lines = _json_signal(combined)
    elif output_kind == "log":
        signal_lines = _repeated_line_signal(lines) or signal_lines
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
        "signal_lines": signal_lines,
        "output_kind": output_kind,
        "evidence": evidence,
        "evidence_fingerprint": hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True).encode()
        ).hexdigest(),
    }
    return finalize_evidence(result)
