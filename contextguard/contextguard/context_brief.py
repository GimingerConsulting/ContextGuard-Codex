from __future__ import annotations

import json
from pathlib import Path

from .ledger import record_ledger
from .utils import estimate_tokens, is_binary, iter_project_files, safe_relpath, sha256_file


DOC_DIRS = ("docs", "doc", "documentation")
DOC_NAMES = {
    "readme.md",
    "agents.md",
    "architecture.md",
    "current_state.md",
    "changelog.md",
    "prd.md",
    "support_ticket.md",
}
DEFAULT_BUDGET_TOKENS = 800


def _is_doc_candidate(root: Path, path: Path) -> bool:
    rel = safe_relpath(path, root).lower()
    name = path.name.lower()
    if name.startswith(".") or ".contextguard-backup-" in rel or is_binary(path):
        return False
    if name in DOC_NAMES:
        return True
    return any(rel.startswith(f"{folder}/") for folder in DOC_DIRS)


def _first_lines(path: Path, limit: int = 6) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [line.strip()[:160] for line in lines[:limit] if line.strip()]


def build_context_map(root: Path, *, max_files: int = 40) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for path in sorted(iter_project_files(root), key=lambda item: item.as_posix()):
        if not _is_doc_candidate(root, path):
            continue
        if path.stat().st_size > 512_000:
            continue
        rel = safe_relpath(path, root)
        entries.append(
            {
                "path": rel,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "lines": sum(1 for _ in path.open("r", encoding="utf-8", errors="replace")),
                "preview": _first_lines(path, limit=3),
            }
        )
        if len(entries) >= max_files:
            break
    return {"version": 1, "files": entries}


def build_context_brief(root: Path, *, budget_tokens: int = DEFAULT_BUDGET_TOKENS) -> tuple[str, dict[str, object]]:
    context_map = build_context_map(root)
    lines = ["ContextGuard context brief (map-first; expand exact file only when needed):"]
    for item in context_map["files"]:
        preview = " | ".join(item["preview"]) if item["preview"] else "(empty)"
        lines.append(
            f"- {item['path']} sha={str(item['sha256'])[:12]} lines={item['lines']} preview={preview}"
        )
    text = "\n".join(lines)
    while estimate_tokens(text) > budget_tokens and len(lines) > 2:
        lines.pop()
        text = "\n".join(lines) + "\n- ... additional mapped docs available via `contextguard expand <path>`"
    record_ledger(root, "brief", bytes_added=len(text.encode()), label="context_brief")
    return text, context_map


def expand_context(root: Path, rel_path: str, *, expected_sha: str | None = None) -> dict[str, object]:
    path = (root / rel_path).resolve()
    safe_relpath(path, root)
    if not path.is_file():
        return {"ok": False, "error": "missing_file", "path": rel_path}
    actual_sha = sha256_file(path)
    if expected_sha and expected_sha not in {actual_sha, actual_sha[:12], actual_sha[: len(expected_sha)]}:
        return {
            "ok": False,
            "error": "sha_mismatch",
            "path": rel_path,
            "expected_sha": expected_sha,
            "actual_sha": actual_sha,
        }
    content = path.read_text(encoding="utf-8", errors="replace")
    record_ledger(root, "expand", bytes_added=len(content.encode()), label=rel_path)
    return {
        "ok": True,
        "path": rel_path,
        "sha256": actual_sha,
        "bytes": len(content.encode()),
        "content": content,
    }


def write_context_map(root: Path, context_map: dict[str, object]) -> Path:
    from .config import state_dir

    path = state_dir(root) / "sessions" / "context_map.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context_map, indent=2) + "\n", encoding="utf-8")
    return path


def load_context_map(root: Path) -> dict[str, object]:
    from .config import state_dir

    path = state_dir(root) / "sessions" / "context_map.json"
    if not path.exists():
        return build_context_map(root)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return build_context_map(root)