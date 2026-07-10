from __future__ import annotations

import json
from pathlib import Path

from contextguard.cli import main


def write_source(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_inspect_command_emits_compact_json(tmp_path: Path, capsys, monkeypatch) -> None:
    root = tmp_path
    first = write_source(root, "src/alpha.py", "def alpha():\n    return 1\n")
    second = write_source(root, "src/beta.py", "class Beta:\n    pass\n")

    monkeypatch.chdir(root)
    exit_code = main(["inspect", "src/alpha.py", "src/beta.py"])
    captured = capsys.readouterr().out.strip()
    payload = json.loads(captured)

    assert exit_code == 0
    assert "\n" not in captured
    assert payload["ok"] is True
    assert payload["command"] == "inspect"
    assert [item["path"] for item in payload["files"]] == ["src/alpha.py", "src/beta.py"]


def test_inspect_command_accepts_one_file(tmp_path: Path, capsys, monkeypatch) -> None:
    root = tmp_path
    first = write_source(root, "src/alpha.py", "def alpha():\n    return 1\n")

    monkeypatch.chdir(root)
    exit_code = main(["inspect", "src/alpha.py"])
    captured = capsys.readouterr().out.strip()
    payload = json.loads(captured)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["file_count"] == 1
