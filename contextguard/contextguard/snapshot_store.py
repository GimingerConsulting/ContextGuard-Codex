from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path

from .config import state_dir
from .ledger import record_ledger
from .utils import safe_relpath


MAX_SNAPSHOT_BYTES = 32_768
MAX_SNAPSHOT_LINES = 200
MAX_DELTA_BYTES = 12_000
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".md", ".sh"}


def _index_path(root: Path) -> Path:
    return state_dir(root) / "snapshots" / "index.json"


def _cas_dir(root: Path) -> Path:
    return state_dir(root) / "snapshots" / "cas"


def _load_index(root: Path) -> dict[str, dict[str, object]]:
    path = _index_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_index(root: Path, data: dict[str, dict[str, object]]) -> None:
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".json.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _resolve(root: Path, value: str) -> tuple[Path, str]:
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    relative = safe_relpath(path, root)
    if not path.is_file():
        raise ValueError("missing_file")
    if path.is_symlink() or path.suffix.lower() not in SOURCE_SUFFIXES:
        raise ValueError("unsafe_file")
    return path, relative


def _content(path: Path) -> str:
    if path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError("file_too_large")
    text = path.read_text(encoding="utf-8")
    if len(text.splitlines()) > MAX_SNAPSHOT_LINES:
        raise ValueError("file_too_long")
    return text


def snapshot_source(root: Path, value: str) -> dict[str, object]:
    root = root.resolve()
    path, relative = _resolve(root, value)
    text = _content(path)
    digest = hashlib.sha256(text.encode()).hexdigest()
    reference = digest[:12]
    cas_dir = _cas_dir(root)
    cas_dir.mkdir(parents=True, exist_ok=True)
    cas_path = cas_dir / f"{digest}.txt"
    if not cas_path.exists():
        cas_path.write_text(text, encoding="utf-8")

    index = _load_index(root)
    previous = index.get(relative)
    index[relative] = {
        "sha256": digest,
        "reference": reference,
        "cas_path": cas_path.as_posix(),
        "line_count": len(text.splitlines()),
        "bytes": len(text.encode()),
    }
    _write_index(root, index)

    if previous and previous.get("sha256") == digest:
        rendered = f"ContextGuard snapshot ref:{reference} unchanged {relative}\n"
        record_ledger(root, "snapshot_unchanged", bytes_saved=max(0, len(text.encode()) - len(rendered.encode())), label=relative)
        return {
            "ok": True,
            "mode": "unchanged",
            "path": relative,
            "reference": reference,
            "sha256": digest,
            "rendered": rendered,
        }

    if previous:
        old_path = Path(str(previous.get("cas_path", "")))
        try:
            old_text = old_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            old_text = ""
        if old_text:
            delta = "".join(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    text.splitlines(keepends=True),
                    fromfile=f"{relative}@{str(previous.get('reference', 'prior'))}",
                    tofile=f"{relative}@{reference}",
                    n=3,
                )
            )
            if delta and len(delta.encode()) <= MAX_DELTA_BYTES:
                rendered = f"ContextGuard snapshot delta {previous.get('reference')}..{reference}\n{delta}"
                record_ledger(root, "snapshot_delta", bytes_saved=max(0, len(text.encode()) - len(rendered.encode())), label=relative)
                return {
                    "ok": True,
                    "mode": "delta",
                    "path": relative,
                    "reference": reference,
                    "previous_reference": previous.get("reference"),
                    "sha256": digest,
                    "rendered": rendered,
                }

    rendered = f"ContextGuard snapshot ref:{reference} {relative}\n{text}"
    record_ledger(root, "snapshot_full", bytes_added=len(rendered.encode()), label=relative)
    return {
        "ok": True,
        "mode": "full",
        "path": relative,
        "reference": reference,
        "sha256": digest,
        "rendered": rendered,
    }
