from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .config import database_path
from .repo_ranker import rank_repository


STOP_TERMS = {
    "add", "and", "change", "code", "create", "efficiency", "feature", "file", "fix",
    "implement", "improve", "output", "project", "test", "tests", "update", "with",
}


def classify_task(root: Path, prompt: str) -> dict:
    terms = {
        t.lower()
        for t in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}", prompt)
        if t.lower() not in STOP_TERMS
    }
    ranked = rank_repository(root, prompt, terms)
    scores = {str(item["path"]): float(item["score"]) for item in ranked}
    reasons = {str(item["path"]): list(item["reasons"]) for item in ranked}
    tests = []
    symbols = []
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
                    scores[path] = scores.get(path, 0.0) + 0.25
                    reasons.setdefault(path, []).append(f"symbol:{name}")
                for path, kind in conn.execute("select path, kind from tests where lower(path) like ? limit 20", (like,)):
                    tests.append(path)
        except Exception:
            pass
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_score = ordered[0][1] if ordered else 0.0
    confidence = "low" if not ordered else "medium" if top_score < 0.2 else "high"
    likely_files = [path for path, _ in ordered]
    return {
        "confidence": confidence,
        "top_score": top_score,
        "retrieval": [
            {"path": path, "score": round(score, 6), "reasons": reasons.get(path, [])}
            for path, score in ordered[:12]
        ],
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
