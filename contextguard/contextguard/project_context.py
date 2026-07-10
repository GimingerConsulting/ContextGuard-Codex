from __future__ import annotations

from pathlib import Path

from .utils import safe_relpath


CONTEXT_FILE_NAMES = (
    "support_ticket.md",
    "ticket.md",
    "prd.md",
    "spec.md",
    "requirements.md",
    "security.md",
)
MAX_CONTEXT_CHARS = 3500


def _candidate_paths(root: Path, likely_files: list[str] | None = None) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for name in CONTEXT_FILE_NAMES:
        path = root / name
        if path.is_file():
            key = path.as_posix()
            if key not in seen:
                seen.add(key)
                candidates.append(path)
    docs = root / "docs"
    if docs.is_dir():
        for name in CONTEXT_FILE_NAMES:
            path = docs / name
            if path.is_file():
                key = path.as_posix()
                if key not in seen:
                    seen.add(key)
                    candidates.append(path)
    for rel in likely_files or []:
        path = root / rel
        if path.is_file() and path.name.lower() in CONTEXT_FILE_NAMES:
            key = path.as_posix()
            if key not in seen:
                seen.add(key)
                candidates.append(path)
    return candidates


def load_project_context(root: Path, *, likely_files: list[str] | None = None, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for path in _candidate_paths(root, likely_files):
        try:
            rel = safe_relpath(path, root)
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        if not text.strip():
            continue
        excerpt = text[:remaining]
        chunks.append(f"[{rel}]\n{excerpt}")
        remaining -= len(excerpt)
        if remaining <= 0:
            break
    return "\n\n".join(chunks)