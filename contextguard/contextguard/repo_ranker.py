from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .utils import iter_project_files, safe_relpath, search_paths_for_terms


SUPPORTED_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".csv", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".json", ".jsonl", ".jsx", ".log", ".md", ".php", ".py",
    ".rb", ".rs", ".sh", ".sql", ".swift", ".toml", ".ts", ".tsx", ".txt",
    ".xml", ".yaml", ".yml",
}
EXCLUDED_PREFIXES = (
    "benchmarks/results/",
    "contextguard/benchmarks/results/",
    ".contextguard/",
    "contextguard/dist/",
    "dist/",
    "build/",
    "coverage/",
)


def is_retrieval_candidate(path: str) -> bool:
    normalized = path.lower().replace("\\", "/").lstrip("./")
    if normalized.startswith(EXCLUDED_PREFIXES):
        return False
    if ".contextguard-backup-" in normalized or normalized.endswith("/.ds_store") or normalized.endswith(".pyc"):
        return False
    return Path(normalized).suffix in SUPPORTED_SUFFIXES


def reciprocal_rank_fusion(
    rankings: list[tuple[list[str], float, str]],
    *,
    k: int = 20,
) -> dict[str, dict[str, object]]:
    fused: dict[str, float] = defaultdict(float)
    reasons: dict[str, list[str]] = defaultdict(list)
    for paths, weight, label in rankings:
        for rank, path in enumerate(paths, 1):
            if not is_retrieval_candidate(path):
                continue
            fused[path] += weight / (k + rank)
            reasons[path].append(label)
    return {path: {"score": score, "reasons": reasons[path]} for path, score in fused.items()}


def _explicit_paths(prompt: str, candidates: list[str]) -> list[str]:
    references = {
        match.lower().strip("`'\"")
        for match in re.findall(r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+", prompt)
    }
    return [
        path
        for path in candidates
        if any(
            path.lower() == ref
            or path.lower().endswith("/" + ref)
            or Path(path.lower()).name == Path(ref).name
            for ref in references
        )
    ]


def rank_repository(root: Path, prompt: str, terms: set[str], *, limit: int = 40) -> list[dict[str, object]]:
    candidates = []
    for path in iter_project_files(root):
        relative = safe_relpath(path, root)
        if is_retrieval_candidate(relative):
            candidates.append(relative)
    explicit = _explicit_paths(prompt, candidates)
    path_scores: list[tuple[float, str]] = []
    for path in candidates:
        lowered = path.lower()
        name = Path(lowered).name
        score = sum(2.0 if term in name else 0.6 for term in terms if term in lowered)
        if score:
            if "/tests/" in f"/{lowered}" or name.startswith("test_"):
                score += 0.3
            path_scores.append((score, path))
    path_ranked = [path for _, path in sorted(path_scores, key=lambda item: (-item[0], item[1]))]
    rankings: list[tuple[list[str], float, str]] = []
    if explicit:
        rankings.append((explicit, 30.0, "explicit_path"))
    if path_ranked:
        rankings.append((path_ranked, 5.0, "path_terms"))
    for term in sorted(terms)[:10]:
        matches = [path for path in search_paths_for_terms(root, {term}, limit=15) if is_retrieval_candidate(path)]
        if matches:
            rankings.append((matches, 1.0, f"content:{term}"))
    fused = reciprocal_rank_fusion(rankings)
    ordered = sorted(fused.items(), key=lambda item: (-float(item[1]["score"]), item[0]))
    return [
        {"path": path, "score": round(float(data["score"]), 6), "reasons": data["reasons"]}
        for path, data in ordered[:limit]
    ]
