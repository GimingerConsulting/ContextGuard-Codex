from pathlib import Path

import pytest

from contextguard.snapshot_store import snapshot_source


def test_snapshot_full_unchanged_and_delta_are_reversible(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text("def value():\n    return 1\n", encoding="utf-8")

    first = snapshot_source(tmp_path, "app.py")
    unchanged = snapshot_source(tmp_path, "app.py")
    source.write_text("def value():\n    return 2\n", encoding="utf-8")
    changed = snapshot_source(tmp_path, "app.py")

    assert first["mode"] == "full"
    assert "return 1" in first["rendered"]
    assert unchanged["mode"] == "unchanged"
    assert "return 1" not in unchanged["rendered"]
    assert changed["mode"] == "delta"
    assert "-    return 1" in changed["rendered"]
    assert "+    return 2" in changed["rendered"]
    assert changed["previous_reference"] == first["reference"]


def test_snapshot_rejects_escape_and_oversized_source(tmp_path: Path):
    outside = tmp_path.parent / "outside.py"
    outside.write_text("secret = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        snapshot_source(tmp_path, str(outside))

    large = tmp_path / "large.py"
    large.write_text("x = 1\n" * 300, encoding="utf-8")
    with pytest.raises(ValueError, match="file_too_long"):
        snapshot_source(tmp_path, "large.py")
