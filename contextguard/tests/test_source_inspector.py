from __future__ import annotations

import json
from pathlib import Path

import pytest

from contextguard.source_inspector import (
    MAX_FILE_BYTES,
    MAX_FILE_LINES,
    MAX_FILES,
    MAX_TOTAL_BYTES,
    MAX_TOTAL_LINES,
    InspectionError,
    inspect_sources,
)


def write_source(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_inspect_sources_returns_stable_compact_payload(tmp_path: Path) -> None:
    root = tmp_path
    first = write_source(root, "src/alpha.py", "def alpha():\n    return 1\n")
    second = write_source(root, "src/beta.py", "class Beta:\n    pass\n")

    result = inspect_sources(root, [first, second])
    again = inspect_sources(root, [first, second])

    assert result["ok"] is True
    assert result["command"] == "inspect"
    assert result["root"] == "."
    assert result["file_count"] == 2
    assert [item["path"] for item in result["files"]] == ["src/alpha.py", "src/beta.py"]
    assert result["files"][0]["fingerprint"] == again["files"][0]["fingerprint"]
    assert result["files"][1]["fingerprint"] == again["files"][1]["fingerprint"]
    compact = json.dumps(result, separators=(",", ":"), sort_keys=True)
    assert "\n" not in compact


def test_inspect_sources_supports_one_file(tmp_path: Path) -> None:
    source = write_source(tmp_path, "src/only.py", "def only():\n    return 1\n")

    result = inspect_sources(tmp_path, [source])

    assert result["file_count"] == 1
    assert result["files"][0]["path"] == "src/only.py"


def test_inspect_sources_supports_symbol_window_in_one_file_and_context_in_companion(tmp_path: Path) -> None:
    root = tmp_path
    source = write_source(
        root,
        "src/window.py",
        "def helper():\n    return 0\n\n\ndef target():\n    return 1\n",
    )
    companion = write_source(root, "src/companion.py", "def sibling():\n    return 2\n")

    result = inspect_sources(root, [source, companion], symbol="target")

    file_entry = result["files"][0]
    assert file_entry["selection"]["symbol"] == "target"
    assert file_entry["selection"]["start_line"] >= 1
    assert file_entry["selection"]["end_line"] == 6
    assert "def target" in file_entry["content"]
    assert file_entry["line_count"] <= MAX_FILE_LINES
    assert result["files"][1]["selection"]["symbol"] is None
    assert "def sibling" in result["files"][1]["content"]


def test_inspect_sources_reads_bounded_window_from_large_source(tmp_path: Path) -> None:
    root = tmp_path
    large = write_source(
        root,
        "src/large.py",
        "\n".join([f"VALUE_{index} = {index}" for index in range(250)] + ["def target():", "    return 1"]) + "\n",
    )
    companion = write_source(root, "src/companion.py", "def helper():\n    return 2\n")

    result = inspect_sources(root, [large, companion], symbol="target")

    assert result["files"][0]["source_line_count"] == 252
    assert result["files"][0]["line_count"] <= 20
    assert "def target" in result["files"][0]["content"]


def test_inspect_sources_range_reads_large_file_with_bounded_result(tmp_path: Path) -> None:
    large = write_source(
        tmp_path,
        "src/huge.py",
        "".join(f"VALUE_{index} = {index}\n" for index in range(20_000)),
    )

    result = inspect_sources(tmp_path, [large], start_line=10_000, end_line=10_020)

    entry = result["files"][0]
    assert entry["source_bytes"] > MAX_FILE_BYTES
    assert entry["line_count"] == 21
    assert "VALUE_9999" in entry["content"]


def test_inspect_sources_reports_missing_file_as_structured_error(tmp_path: Path) -> None:
    safe = write_source(tmp_path, "src/safe.py", "VALUE = 1\n")

    with pytest.raises(InspectionError) as excinfo:
        inspect_sources(tmp_path, [safe, "src/missing.py"])

    assert excinfo.value.code == "missing_file"


@pytest.mark.parametrize(
    ("relative", "expected_code"),
    [
        ("../outside.py", "path_escape"),
        ("src/dir", "directory"),
        ("build/output.log", "unsafe_file"),
    ],
)
def test_inspect_sources_rejects_unsafe_paths(tmp_path: Path, relative: str, expected_code: str) -> None:
    root = tmp_path
    safe = write_source(root, "src/safe.py", "print('safe')\n")
    target = root / relative
    if relative.endswith("/dir"):
        target.mkdir(parents=True)
    elif relative.startswith(".."):
        outside = tmp_path.parent / "outside.py"
        outside.write_text("print('outside')\n", encoding="utf-8")
        target = outside
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith(".json"):
            target.write_text('{"value": 1}\n', encoding="utf-8")
        else:
            target.write_text("log line\n", encoding="utf-8")

    with pytest.raises(InspectionError) as excinfo:
        inspect_sources(root, [safe, target])

    assert excinfo.value.code == expected_code


def test_inspect_sources_summarizes_structured_files_without_raw_values(tmp_path: Path) -> None:
    log = write_source(
        tmp_path,
        "data/production.log",
        "INFO request id=123 status=200\nERROR database password=super-secret status=500\n",
    )
    jsonl = write_source(
        tmp_path,
        "data/events.jsonl",
        '{"event":"created","token":"hidden-value"}\n{"event":"updated","token":"other"}\n',
    )
    payload = write_source(tmp_path, "data/scenario.json", '{"sku":"ABC","secret":"do-not-show"}\n')
    csv = write_source(tmp_path, "data/export.csv", "name,credential\nAlice,private-value\n")

    result = inspect_sources(tmp_path, [log, jsonl, payload, csv])

    assert result["file_count"] == 4
    assert all(item["selection"]["mode"] == "structured_summary" for item in result["files"])
    rendered = json.dumps(result)
    assert "observed_keys" in rendered
    assert "severity_counts" in rendered
    assert "super-secret" not in rendered
    assert "hidden-value" not in rendered
    assert "do-not-show" not in rendered
    assert "private-value" not in rendered


def test_inspect_sources_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path
    safe = write_source(root, "src/safe.py", "print('safe')\n")
    outside = tmp_path.parent / "outside.py"
    outside.write_text("print('escape')\n", encoding="utf-8")
    link = root / "src/link.py"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)

    with pytest.raises(InspectionError) as excinfo:
        inspect_sources(root, [safe, link])

    assert excinfo.value.code == "path_escape"


def test_inspect_sources_rejects_repeated_files(tmp_path: Path) -> None:
    root = tmp_path
    source = write_source(root, "src/repeat.py", "print('repeat')\n")

    with pytest.raises(InspectionError) as excinfo:
        inspect_sources(root, [source, root / "src" / "." / "repeat.py"])

    assert excinfo.value.code == "duplicate_file"


def test_inspect_sources_enforces_byte_and_line_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path
    files = [
        write_source(root, "src/one.py", "line 1\nline 2\nline 3\n"),
        write_source(root, "src/two.py", "line 1\nline 2\nline 3\n"),
        write_source(root, "src/three.py", "line 1\nline 2\nline 3\n"),
    ]

    monkeypatch.setattr("contextguard.source_inspector.MAX_FILE_BYTES", 12)
    monkeypatch.setattr("contextguard.source_inspector.MAX_TOTAL_BYTES", 20)
    monkeypatch.setattr("contextguard.source_inspector.MAX_FILE_LINES", 2)
    monkeypatch.setattr("contextguard.source_inspector.MAX_TOTAL_LINES", 5)

    with pytest.raises(InspectionError) as excinfo:
        inspect_sources(root, files[:2])
    assert excinfo.value.code == "file_too_large"

    monkeypatch.setattr("contextguard.source_inspector.MAX_FILE_BYTES", MAX_FILE_BYTES)
    monkeypatch.setattr("contextguard.source_inspector.MAX_FILE_LINES", MAX_FILE_LINES)

    with pytest.raises(InspectionError) as excinfo:
        inspect_sources(root, files)
    assert excinfo.value.code == "total_too_large"
