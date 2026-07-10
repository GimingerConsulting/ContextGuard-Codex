from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .family_codec import render_family_codec_brief
from .utils import estimate_tokens, iter_project_files, safe_relpath, sha256_file


FAMILY_PATTERNS = (
    (re.compile(r"architecture", re.I), "architecture"),
    (re.compile(r"changelog|changes", re.I), "changelog"),
    (re.compile(r"readme", re.I), "readme"),
    (re.compile(r"prd|requirements|spec", re.I), "spec"),
    (re.compile(r"report|summary", re.I), "report"),
    (re.compile(r"support|ticket", re.I), "support"),
)


def classify_family(name: str) -> str:
    for pattern, label in FAMILY_PATTERNS:
        if pattern.search(name):
            return label
    return "other"


def build_doc_families(root: Path, *, max_per_family: int = 8) -> dict[str, list[dict[str, object]]]:
    families: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in iter_project_files(root):
        if path.suffix.lower() not in {".md", ".txt", ".rst"}:
            continue
        if ".contextguard-backup-" in path.as_posix():
            continue
        rel = safe_relpath(path, root)
        family = classify_family(path.name)
        if family == "other":
            continue
        if len(families[family]) >= max_per_family:
            continue
        families[family].append(
            {
                "path": rel,
                "sha256": sha256_file(path)[:12],
                "bytes": path.stat().st_size,
                "tokens_est": estimate_tokens(path.read_text(encoding="utf-8", errors="replace")[:4000]),
            }
        )
    return {key: sorted(values, key=lambda item: str(item["path"])) for key, values in sorted(families.items())}


def render_doc_families_brief(root: Path, *, budget_lines: int = 14) -> str:
    families = build_doc_families(root)
    return render_family_codec_brief(families, budget_lines=budget_lines)