from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from .utils import is_binary, safe_relpath

MIN_FILES = 2
MAX_FILES = 4
MAX_FILE_BYTES = 32_768
MAX_TOTAL_BYTES = 96_000
MAX_FILE_LINES = 200
MAX_TOTAL_LINES = 500
SYMBOL_WINDOW_LINES = 20

_UNSAFE_DIRS = {
    ".git",
    ".contextguard",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "coverage",
    "artifacts",
    "artifact",
    "generated",
    "logs",
    "log",
    "reports",
    "tmp",
    "temp",
}
_UNSAFE_SUFFIXES = {
    ".bin",
    ".csv",
    ".db",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".json",
    ".jsonl",
    ".log",
    ".pdf",
    ".png",
    ".sqlite",
    ".svg",
    ".tsv",
    ".xml",
    ".yaml",
    ".yml",
    ".zip",
}


class InspectionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _raise(code: str, message: str) -> None:
    raise InspectionError(code, message)


def _resolve_candidate(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    absolute = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved = absolute.resolve(strict=True)
    except FileNotFoundError:
        _raise("missing_file", f"source file does not exist: {candidate}")
    if resolved != resolved_root and resolved_root not in resolved.parents:
        _raise("path_escape", f"path escapes project root: {candidate}")
    return resolved


def _is_unsafe_source(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & _UNSAFE_DIRS:
        return True
    if path.suffix.lower() in _UNSAFE_SUFFIXES:
        return True
    if path.name.startswith(".") and path.suffix.lower() not in {".py", ".sh"}:
        return True
    return False


def _select_window(lines: list[str], symbol: str | None, start_line: int | None, end_line: int | None) -> tuple[int, int]:
    total = len(lines)
    if start_line is not None or end_line is not None:
        start = 1 if start_line is None else start_line
        end = total if end_line is None else end_line
        if start < 1 or end < start:
            _raise("invalid_range", "invalid line range")
        selected_end = min(end, total)
        if selected_end - start + 1 > MAX_FILE_LINES:
            _raise("range_too_large", f"line range exceeds {MAX_FILE_LINES} lines")
        return start, selected_end
    if symbol:
        pattern = re.compile(rf"^\s*(?:def|class)\s+{re.escape(symbol)}\b")
        for index, line in enumerate(lines, 1):
            if pattern.search(line) or re.search(rf"\b{re.escape(symbol)}\b", line):
                start = max(1, index - (SYMBOL_WINDOW_LINES // 2))
                end = min(total, start + SYMBOL_WINDOW_LINES - 1)
                return start, end
        _raise("symbol_not_found", f"symbol not found: {symbol}")
    return 1, min(total, MAX_FILE_LINES)


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _as_lines(text: str) -> list[str]:
    return text.splitlines()


def inspect_sources(
    root: Path,
    files: Iterable[Path | str],
    *,
    symbol: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict[str, object]:
    root = root.resolve()
    requested = [Path(file) for file in files]
    if not (MIN_FILES <= len(requested) <= MAX_FILES):
        _raise("file_count", f"expected {MIN_FILES}-{MAX_FILES} files")

    resolved_files: list[Path] = []
    seen: set[Path] = set()
    total_bytes = 0
    total_lines = 0
    entries: list[dict[str, object]] = []
    symbol_matched = False

    for candidate in requested:
        resolved = _resolve_candidate(root, candidate)
        if resolved in seen:
            _raise("duplicate_file", f"duplicate file argument: {candidate}")
        seen.add(resolved)
        resolved_files.append(resolved)
        if resolved.is_dir():
            _raise("directory", f"directory is not a source file: {candidate}")
        if resolved.is_symlink():
            _raise("path_escape", f"symlink escapes project root: {candidate}")
        if _is_unsafe_source(resolved):
            _raise("unsafe_file", f"unsafe file category: {candidate}")
        if is_binary(resolved):
            _raise("unsafe_file", f"binary file is not supported: {candidate}")

        raw = resolved.read_bytes()
        size = len(raw)
        if size > MAX_FILE_BYTES:
            _raise("file_too_large", f"file exceeds byte limit: {candidate}")
        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            _raise("total_too_large", "combined file bytes exceed limit")

        text = raw.decode("utf-8")
        lines = _as_lines(text)
        line_count = len(lines)

        selected_symbol = symbol
        try:
            selected_start, selected_end = _select_window(lines, symbol, start_line, end_line)
            symbol_matched = symbol_matched or bool(symbol)
        except InspectionError as exc:
            if exc.code != "symbol_not_found" or start_line is not None or end_line is not None:
                raise
            selected_symbol = None
            selected_start, selected_end = _select_window(lines, None, None, None)
        selected_lines = lines[selected_start - 1:selected_end]
        total_lines += len(selected_lines)
        if total_lines > MAX_TOTAL_LINES:
            _raise("total_too_large", "combined file lines exceed limit")
        entries.append(
            {
                "path": safe_relpath(resolved, root),
                "bytes": size,
                "line_count": len(selected_lines),
                "source_line_count": line_count,
                "fingerprint": _fingerprint(text),
                "selection": {
                    "symbol": selected_symbol,
                    "start_line": selected_start,
                    "end_line": selected_end,
                },
                "content": "\n".join(selected_lines),
            }
        )

    if symbol and not symbol_matched:
        _raise("symbol_not_found", f"symbol not found: {symbol}")

    return {
        "ok": True,
        "command": "inspect",
        "root": safe_relpath(root, root),
        "file_count": len(entries),
        "files": entries,
        "limits": {
            "min_files": MIN_FILES,
            "max_files": MAX_FILES,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_total_bytes": MAX_TOTAL_BYTES,
            "max_file_lines": MAX_FILE_LINES,
            "max_total_lines": MAX_TOTAL_LINES,
        },
    }
