from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .config import database_path
from .utils import iter_project_files, safe_relpath, search_paths_for_terms


STOP_TERMS = {
    "add", "and", "change", "code", "create", "efficiency", "feature", "file", "fix",
    "implement", "improve", "output", "project", "test", "tests", "update", "with",
}


def classify_task(root: Path, prompt: str) -> dict:
    lowered_prompt = prompt.lower()
    terms = {
        t.lower()
        for t in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}", prompt)
        if t.lower() not in STOP_TERMS
    }
    candidates = []
    tests = []
    symbols = []
    for path in iter_project_files(root):
        rel = safe_relpath(path, root)
        low = rel.lower()
        score = sum(1 for term in terms if term in low)
        if low in lowered_prompt or Path(low).name in lowered_prompt:
            score += 10
        if score:
            candidates.append((score, rel))
    for rel in search_paths_for_terms(root, terms):
        candidates.append((2, rel))
    db_path = database_path(root)
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            for term in terms:
                like = f"%{term}%"
                for name, kind, path, line in conn.execute(
                    "select name, kind, path, line from symbols where lower(name) like ? limit 20",
                    (like,),
                ):
                    symbols.append({"name": name, "kind": kind, "path": path, "line": line})
                    candidates.append((3, path))
                for path, kind in conn.execute("select path, kind from tests where lower(path) like ? limit 20", (like,)):
                    tests.append(path)
        except Exception:
            pass
    candidates.sort(reverse=True)
    top_score = candidates[0][0] if candidates else 0
    confidence = "low" if not candidates else "medium" if top_score < 2 else "high"
    likely_files = []
    for _, rel in candidates:
        if rel not in likely_files:
            likely_files.append(rel)
    return {
        "confidence": confidence,
        "top_score": top_score,
        "likely_files": likely_files[:12] if confidence != "low" else [],
        "likely_symbols": symbols[:12] if confidence != "low" else [],
        "relevant_tests": tests[:8] if confidence != "low" else [],
        "recommended_scope": "Use metadata and symbol/range inspection first; expand only when evidence is insufficient.",
        "retrieval_levels": [
            "metadata", "symbol_location", "relevant_lines", "complete_symbol",
            "callers_and_dependencies", "complete_file", "wider_repository",
        ],
        "escalate_when": [
            "ambiguous_root_cause", "missing_types_or_imports", "contradicting_test",
            "module_boundary", "security_or_persistence", "insufficient_confidence",
            "architectural_change",
        ],
    }
