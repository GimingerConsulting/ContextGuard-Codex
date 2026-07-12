from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import deque
from pathlib import Path
from typing import Iterable

from .utils import is_binary, safe_relpath
from .large_file import summarize_large_file

MIN_FILES = 1
MAX_FILES = 4
MAX_FILE_BYTES = 32_768
MAX_SCAN_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 96_000
MAX_FILE_LINES = 200
MAX_TOTAL_LINES = 500
SYMBOL_WINDOW_LINES = 20
MAX_OUTLINE_LINES = 16
MAX_OUTLINE_LINE_CHARS = 300
MAX_OUTLINE_IMPORT_LINES = 4

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
_STRUCTURED_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".tsv"}
_ALWAYS_UNSAFE_DIRS = {".git", ".contextguard", ".venv", "__pycache__", "build", "dist", "generated", "tmp", "temp"}


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


def _structured_allowed(path: Path) -> bool:
    return path.suffix.lower() in _STRUCTURED_SUFFIXES and not ({part.lower() for part in path.parts} & _ALWAYS_UNSAFE_DIRS)


def _file_stats(path: Path) -> tuple[str, int, int]:
    hasher = hashlib.sha256()
    line_count = 0
    size = 0
    with path.open("rb") as handle:
        for raw_line in handle:
            size += len(raw_line)
            if size > MAX_SCAN_BYTES:
                _raise("file_too_large", f"file exceeds scan limit: {path}")
            hasher.update(raw_line)
            line_count += 1
    return hasher.hexdigest(), line_count, size


def _structured_summary(path: Path, root: Path) -> tuple[str, str, int, int]:
    fingerprint, line_count, source_bytes = _file_stats(path)
    result = summarize_large_file(path, limit=2)
    suffix = path.suffix.lower()
    allowed = {
        ".json": ("size", "top_level_type", "keys", "sample", "records", "sample_types", "observed_keys"),
        ".jsonl": ("records", "invalid_records", "observed_keys"),
        ".csv": ("records", "columns", "null_counts"),
        ".tsv": ("records", "columns", "null_counts"),
        ".log": ("size", "line_count", "severity_counts", "error_signatures"),
    }[suffix]
    payload = {key: result[key] for key in allowed if key in result}
    if "error_signatures" in payload:
        payload["error_signatures"] = [str(item)[:180] for item in payload["error_signatures"][:2]]
    content = "mode=structured_summary;" + ";".join(
        f"{key}={json.dumps(value, separators=(',', ':'), sort_keys=True)}"
        for key, value in payload.items()
    )
    return content, fingerprint, line_count, source_bytes


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


def _compact_outline_line(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= MAX_OUTLINE_LINE_CHARS:
        return compact
    return compact[: MAX_OUTLINE_LINE_CHARS - 1] + "…"


def _python_outline(text: str) -> list[str] | None:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None

    outline: list[str] = []
    import_count = 0

    def add(line: int, depth: int, value: str) -> None:
        if len(outline) < min(MAX_OUTLINE_LINES, MAX_FILE_LINES):
            outline.append(f"L{line} {'  ' * depth}{_compact_outline_line(value)}")

    def visit(nodes: list[ast.stmt], depth: int = 0) -> None:
        nonlocal import_count
        for node in nodes:
            if len(outline) >= min(MAX_OUTLINE_LINES, MAX_FILE_LINES):
                return
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if import_count < MAX_OUTLINE_IMPORT_LINES:
                    add(node.lineno, depth, ast.unparse(node))
                    import_count += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    add(decorator.lineno, depth, f"@{ast.unparse(decorator)}")
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
                add(node.lineno, depth, f"{prefix} {node.name}({ast.unparse(node.args)}){returns}:")
                visit([item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))], depth + 1)
            elif isinstance(node, ast.ClassDef):
                for decorator in node.decorator_list:
                    add(decorator.lineno, depth, f"@{ast.unparse(decorator)}")
                bases = [ast.unparse(base) for base in node.bases]
                bases.extend(f"{keyword.arg}={ast.unparse(keyword.value)}" for keyword in node.keywords)
                suffix = f"({', '.join(bases)})" if bases else ""
                add(node.lineno, depth, f"class {node.name}{suffix}:")
                visit(node.body, depth + 1)
            elif depth == 0 and isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [ast.unparse(target) for target in targets if isinstance(target, (ast.Name, ast.Attribute))]
                if names:
                    annotation = f": {ast.unparse(node.annotation)}" if isinstance(node, ast.AnnAssign) else ""
                    add(node.lineno, depth, f"{', '.join(names)}{annotation}")

    try:
        visit(tree.body)
    except (RecursionError, ValueError):
        return None
    return outline


_GENERIC_DECLARATION = re.compile(
    r"^\s*(?:(?:export|declare|default|public|private|protected|static|abstract)\s+)*"
    r"(?:import\b|(?:async\s+)?function\b|class\b|interface\b|type\b|enum\b|namespace\b|"
    r"(?:const|let|var)\s+[A-Za-z_$][\w$]*(?:\s*[:=]|\s*$))"
)


def _generic_outline(lines: list[str]) -> list[str]:
    limit = min(MAX_OUTLINE_LINES, MAX_FILE_LINES)
    declarations = [
        f"L{index} {_compact_outline_line(line)}"
        for index, line in enumerate(lines, 1)
        if line == line.lstrip() and _GENERIC_DECLARATION.match(line)
    ]
    if declarations:
        imports = [line for line in declarations if re.match(r"^L\d+ import\b", line)]
        non_imports = [line for line in declarations if line not in imports]
        return (imports[:MAX_OUTLINE_IMPORT_LINES] + non_imports)[:limit]
    return [f"L{index} {_compact_outline_line(line)}" for index, line in enumerate(lines, 1) if line.strip()][:limit]


def _read_source_outline(path: Path) -> tuple[list[str], str, int, int, str]:
    """Read an allowed-size source and return a deterministic structural outline."""
    hasher = hashlib.sha256()
    raw_parts: list[bytes] = []
    total_lines = 0
    total_bytes = 0
    with path.open("rb") as handle:
        for raw_line in handle:
            total_bytes += len(raw_line)
            if total_bytes > MAX_SCAN_BYTES:
                _raise("file_too_large", f"file exceeds scan limit: {path}")
            hasher.update(raw_line)
            total_lines += 1
            if total_bytes <= MAX_FILE_BYTES:
                raw_parts.append(raw_line)
    if total_bytes > MAX_FILE_BYTES:
        _raise("file_too_large", f"file exceeds byte limit: {path}")

    text = b"".join(raw_parts).decode("utf-8", errors="replace")
    lines = text.splitlines()
    python_outline = _python_outline(text) if path.suffix.lower() == ".py" else None
    return python_outline if python_outline is not None else _generic_outline(lines), hasher.hexdigest(), total_lines, total_bytes, "python_ast" if python_outline is not None else "generic"


def _read_selected_source(
    path: Path,
    *,
    symbol: str | None,
    start_line: int | None,
    end_line: int | None,
) -> tuple[list[str], int, int, str, int, int]:
    """Scan a source file with bounded memory and retain only the requested window."""
    explicit_range = start_line is not None or end_line is not None
    if explicit_range:
        requested_start = 1 if start_line is None else start_line
        requested_end = requested_start + MAX_FILE_LINES - 1 if end_line is None else end_line
        if requested_start < 1 or requested_end < requested_start:
            _raise("invalid_range", "invalid line range")
        if requested_end - requested_start + 1 > MAX_FILE_LINES:
            _raise("range_too_large", f"line range exceeds {MAX_FILE_LINES} lines")
    else:
        requested_start = 1
        requested_end = MAX_FILE_LINES

    hasher = hashlib.sha256()
    selected: list[str] = []
    before: deque[tuple[int, str]] = deque(maxlen=SYMBOL_WINDOW_LINES // 2)
    symbol_line: int | None = None
    total_lines = 0
    total_bytes = 0
    after_remaining = 0
    pattern = re.compile(rf"^\s*(?:def|class)\s+{re.escape(symbol)}\b|\b{re.escape(symbol)}\b") if symbol else None

    with path.open("rb") as handle:
        for raw_line in handle:
            total_bytes += len(raw_line)
            if total_bytes > MAX_SCAN_BYTES:
                _raise("file_too_large", f"file exceeds scan limit: {path}")
            hasher.update(raw_line)
            total_lines += 1
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if explicit_range:
                if requested_start <= total_lines <= requested_end:
                    selected.append(line)
                continue
            if symbol:
                if symbol_line is None and pattern and pattern.search(line):
                    symbol_line = total_lines
                    selected.extend(item for _, item in before)
                    selected.append(line)
                    after_remaining = SYMBOL_WINDOW_LINES - len(selected)
                elif symbol_line is not None and after_remaining > 0:
                    selected.append(line)
                    after_remaining -= 1
                elif symbol_line is None:
                    before.append((total_lines, line))
                continue
            if total_lines <= MAX_FILE_LINES:
                selected.append(line)

    if total_bytes > MAX_FILE_BYTES and not (explicit_range or symbol):
        _raise("file_too_large", f"file exceeds byte limit: {path}")
    if symbol and symbol_line is None:
        _raise("symbol_not_found", f"symbol not found: {symbol}")
    if explicit_range:
        selected_start = requested_start
    elif symbol_line is not None:
        selected_start = max(1, symbol_line - (SYMBOL_WINDOW_LINES // 2))
    else:
        selected_start = 1
    selected_end = selected_start + len(selected) - 1 if selected else selected_start - 1
    return selected, selected_start, selected_end, hasher.hexdigest(), total_lines, total_bytes


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
        structured = _structured_allowed(resolved)
        if _is_unsafe_source(resolved) and not structured:
            _raise("unsafe_file", f"unsafe file category: {candidate}")
        if is_binary(resolved):
            _raise("unsafe_file", f"binary file is not supported: {candidate}")

        selected_symbol = symbol
        if structured:
            if symbol or start_line is not None or end_line is not None:
                _raise("invalid_selection", "structured inspection uses automatic summaries, not source ranges or symbols")
            content, fingerprint, line_count, source_bytes = _structured_summary(resolved, root)
            selected_lines = [content]
            selected_start, selected_end = 1, 1
            selected_symbol = None
        else:
            outline_format: str | None = None
            if symbol is None and start_line is None and end_line is None:
                selected_lines, fingerprint, line_count, source_bytes, outline_format = _read_source_outline(resolved)
                selected_start, selected_end = 1, line_count
            else:
                try:
                    selected_lines, selected_start, selected_end, fingerprint, line_count, source_bytes = _read_selected_source(
                        resolved, symbol=symbol, start_line=start_line, end_line=end_line
                    )
                    symbol_matched = symbol_matched or bool(symbol)
                except InspectionError as exc:
                    if exc.code != "symbol_not_found" or start_line is not None or end_line is not None:
                        raise
                    selected_symbol = None
                    selected_lines, selected_start, selected_end, fingerprint, line_count, source_bytes = _read_selected_source(
                        resolved, symbol=None, start_line=None, end_line=None
                    )
        selected_bytes = len("\n".join(selected_lines).encode("utf-8"))
        total_bytes += selected_bytes
        if total_bytes > MAX_TOTAL_BYTES:
            _raise("total_too_large", "combined selected bytes exceed limit")
        total_lines += len(selected_lines)
        if total_lines > MAX_TOTAL_LINES:
            _raise("total_too_large", "combined file lines exceed limit")
        if structured:
            entries.append(
                {
                    "path": safe_relpath(resolved, root),
                    "source_bytes": source_bytes,
                    "fingerprint": fingerprint[:12],
                    "selection": {"mode": "structured_summary"},
                    "content": "\n".join(selected_lines),
                }
            )
        else:
            selection: dict[str, object]
            if outline_format:
                selection = {"mode": "outline", "format": outline_format, "symbol": None}
            else:
                selection = {
                    "mode": "source",
                    "symbol": selected_symbol,
                    "start_line": selected_start,
                    "end_line": selected_end,
                }
            entries.append(
                {
                    "path": safe_relpath(resolved, root),
                    "bytes": selected_bytes,
                    "source_bytes": source_bytes,
                    "line_count": len(selected_lines),
                    "source_line_count": line_count,
                    "fingerprint": fingerprint,
                    "selection": selection,
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
