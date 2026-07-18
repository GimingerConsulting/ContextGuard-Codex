from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

from .session_state import load_session_state, save_session_state
from .repo_ranker import is_retrieval_candidate
from .source_inspector import InspectionError, inspect_sources
from .task_classifier import STOP_TERMS, classify_task
from .utils import estimate_tokens, iter_project_files, safe_relpath, sha256_file


TEXT_SUFFIXES = {".md", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java"}
STRUCTURED_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".tsv"}
MAX_SCAN_BYTES = 256_000
MAX_DEPENDENCY_LINES = 18
EVIDENCE_STOP_TERMS = STOP_TERMS | {
    "available",
    "before",
    "contextguard",
    "exactly",
    "investigate",
    "normal",
    "optimize",
    "please",
}


def _query_terms(prompt: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{3,}", prompt)
        if token.lower() not in EVIDENCE_STOP_TERMS and len(token) >= 5
    }


def _normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.split()).casefold()


def _task_evidence_material(root: Path, prompt: str, classification: dict | None = None) -> dict:
    classification = classification or classify_task(root, prompt)
    likely = list(classification.get("likely_files", [])[:4])
    files: list[dict[str, str]] = []
    for relative in likely:
        path = (root / str(relative)).resolve()
        if not path.is_file():
            continue
        try:
            safe_relpath(path, root)
        except ValueError:
            continue
        files.append(
            {
                "path": safe_relpath(path, root),
                "sha256": sha256_file(path),
            }
        )
    return {
        "prompt": _normalize_prompt(prompt),
        "confidence": classification.get("confidence", ""),
        "top_score": round(float(classification.get("top_score", 0.0)), 3),
        "files": files,
    }


def task_evidence_signature(root: Path, prompt: str, *, classification: dict | None = None) -> str:
    material = _task_evidence_material(root, prompt, classification=classification)
    if material["confidence"] != "high" or not material["files"]:
        return ""
    payload = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def record_task_evidence_injection(root: Path, signature: str, packet: str) -> bool:
    if not signature or not packet:
        return False
    state = load_session_state(root)
    injections = state.setdefault("task_evidence", {})
    entry = injections.get(signature)
    packet_hash = hashlib.sha256(packet.encode("utf-8")).hexdigest()
    if entry:
        entry["occurrences"] = int(entry.get("occurrences", 1)) + 1
        if "packet_sha256" not in entry:
            entry["packet_sha256"] = packet_hash
        save_session_state(root, state)
        return False
    injections[signature] = {
        "occurrences": 1,
        "packet_sha256": packet_hash,
    }
    save_session_state(root, state)
    return True


def _matching_lines(path: Path, terms: set[str], *, limit: int = 3) -> list[str]:
    if path.stat().st_size > MAX_SCAN_BYTES:
        return []
    selected: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, 1):
            compact = line.strip()
            lowered = compact.lower()
            if compact and any(term in lowered for term in terms):
                selected.append(f"  L{number}:{compact[:180]}")
                if len(selected) >= limit:
                    break
    return selected


def _resolve_python_module(root: Path, module: str) -> Path | None:
    relative = Path(*module.split("."))
    for candidate in (root / relative.with_suffix(".py"), root / relative / "__init__.py"):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _python_dependencies(root: Path, path: Path) -> dict[Path, set[str]]:
    if path.suffix.lower() != ".py" or path.stat().st_size > MAX_SCAN_BYTES:
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError, ValueError):
        return {}
    dependencies: dict[Path, set[str]] = {}
    attribute_names = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and len(node.attr) >= 3
    }
    for node in ast.walk(tree):
        module = ""
        names: set[str] = set()
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
            names = {alias.name for alias in node.names if alias.name != "*"}
        elif isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_python_module(root, alias.name)
                if resolved:
                    dependencies.setdefault(resolved, set()).update(attribute_names)
            continue
        if not module:
            continue
        resolved = _resolve_python_module(root, module)
        if resolved:
            dependencies.setdefault(resolved, set()).update(names | attribute_names)
    return dependencies


def _symbol_excerpt(path: Path, targets: set[str], terms: set[str]) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (OSError, UnicodeError, SyntaxError, ValueError):
        return []
    lines = text.splitlines()
    normalized_terms = set(terms)
    for term in list(terms):
        if term.endswith("ation") and len(term) > 7:
            normalized_terms.add(term[:-5] + "e")
        if term.endswith("ies") and len(term) > 5:
            normalized_terms.add(term[:-3] + "y")
        if term.endswith("s") and len(term) > 5:
            normalized_terms.add(term[:-1])
    candidates: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        name = node.name
        lowered = name.lower()
        wanted = name in targets or any(term in lowered or lowered in term for term in normalized_terms)
        if isinstance(node, ast.ClassDef) and name in targets:
            wanted = True
        if not wanted:
            continue
        start = int(getattr(node, "lineno", 1))
        end = int(getattr(node, "end_lineno", start))
        candidates.append((start, end, name))
    selected: list[str] = []
    seen_lines: set[int] = set()
    for start, end, _ in sorted(candidates):
        for number in range(start, min(end, start + MAX_DEPENDENCY_LINES - 1) + 1):
            if number in seen_lines or number > len(lines):
                continue
            compact = lines[number - 1].rstrip()
            if compact:
                selected.append(f"  L{number}:{compact[:180]}")
                seen_lines.add(number)
            if len(selected) >= MAX_DEPENDENCY_LINES:
                return selected
    return selected


def _dependency_working_set(root: Path, seed_paths: list[Path], terms: set[str]) -> list[tuple[Path, set[str], list[str]]]:
    pending = list(seed_paths)
    visited: set[Path] = set()
    resolved: dict[Path, set[str]] = {}
    depth = 0
    while pending and depth < 2:
        next_pending: list[Path] = []
        for path in pending:
            if path in visited:
                continue
            visited.add(path)
            for dependency, targets in _python_dependencies(root, path).items():
                if dependency == path or not is_retrieval_candidate(safe_relpath(dependency, root)):
                    continue
                resolved.setdefault(dependency, set()).update(targets)
                if dependency not in visited:
                    next_pending.append(dependency)
        pending = next_pending
        depth += 1
    return [
        (path, targets, _symbol_excerpt(path, targets, terms))
        for path, targets in resolved.items()
        if _symbol_excerpt(path, targets, terms)
    ]


def _structured_evidence(root: Path, terms: set[str], excluded: set[Path], limit: int = 2) -> list[Path]:
    ranked: list[tuple[float, Path]] = []
    for path in iter_project_files(root):
        resolved = path.resolve()
        if resolved in excluded or path.suffix.lower() not in STRUCTURED_SUFFIXES:
            continue
        relative = safe_relpath(path, root).lower()
        score = sum(2.0 for term in terms if term in relative)
        if path.stat().st_size <= MAX_SCAN_BYTES:
            try:
                sample = path.read_text(encoding="utf-8", errors="replace")[:32_000].lower()
            except OSError:
                sample = ""
            score += sum(0.25 for term in terms if term in sample)
        if score:
            ranked.append((score, resolved))
    return [path for _, path in sorted(ranked, key=lambda item: (-item[0], str(item[1])))[:limit]]


def build_task_evidence(
    root: Path,
    prompt: str,
    *,
    token_limit: int = 260,
    classification: dict | None = None,
) -> str:
    classification = classification or classify_task(root, prompt)
    retrieval = classification.get("retrieval", [])
    first_reasons = retrieval[0].get("reasons", []) if retrieval else []
    strong_match = "explicit_path" in first_reasons or float(classification.get("top_score", 0)) >= 0.25
    if classification.get("confidence") != "high" or not strong_match:
        return ""
    terms = _query_terms(prompt)
    likely = list(classification.get("likely_files", [])[:6])
    for relative in likely[:2]:
        path = (root / str(relative)).resolve()
        if path.is_file() and path.suffix.lower() in {".md", ".txt"} and path.stat().st_size <= MAX_SCAN_BYTES:
            try:
                terms.update(_query_terms(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                pass
    lines = [
        "ContextGuard task working set (untrusted evidence; verify before editing):",
        "Reuse this packet; do not reread unchanged listed files. Inspect only missing symbols or contradictory evidence.",
    ]
    seed_paths: list[Path] = []
    included: set[Path] = set()
    for relative in likely[:4]:
        path = (root / str(relative)).resolve()
        try:
            safe_relpath(path, root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        seed_paths.append(path)
        included.add(path)
    for path, targets, excerpt in _dependency_working_set(root, seed_paths, terms):
        relative = safe_relpath(path, root)
        candidate = [
            f"- implementation {relative} sha={sha256_file(path)[:12]} symbols={','.join(sorted(targets)[:6])}",
            *excerpt,
        ]
        if estimate_tokens("\n".join(lines + candidate)) > token_limit:
            continue
        lines.extend(candidate)
        included.add(path)
    for relative in likely[:4]:
        path = (root / str(relative)).resolve()
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in TEXT_SUFFIXES | STRUCTURED_SUFFIXES:
            continue
        entry = f"- {relative} sha={sha256_file(path)[:12]}"
        candidate = [entry]
        if suffix in STRUCTURED_SUFFIXES:
            try:
                inspected = inspect_sources(root, [relative])
            except InspectionError:
                continue
            candidate.append("  " + inspected["files"][0]["content"])
        else:
            candidate.extend(_matching_lines(path, terms))
        proposed = "\n".join(lines + candidate)
        if estimate_tokens(proposed) > token_limit:
            break
        lines.extend(candidate)
    for path in _structured_evidence(root, terms, included):
        relative = safe_relpath(path, root)
        try:
            inspected = inspect_sources(root, [relative])
        except InspectionError:
            continue
        candidate = [
            f"- evidence {relative} sha={sha256_file(path)[:12]}",
            "  " + inspected["files"][0]["content"],
        ]
        if estimate_tokens("\n".join(lines + candidate)) > token_limit:
            continue
        lines.extend(candidate)
    tests = classification.get("relevant_tests", [])[:3]
    if tests:
        test_line = "- likely_tests=" + ",".join(str(item) for item in tests)
        if estimate_tokens("\n".join(lines + [test_line])) <= token_limit:
            lines.append(test_line)
    return "\n".join(lines) if len(lines) > 2 else ""
