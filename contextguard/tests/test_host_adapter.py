from pathlib import Path

from contextguard.host_adapter import codex_home, render_codex_note


def test_codex_home_defaults_to_user_codex(monkeypatch, tmp_path):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    assert codex_home() == Path.home() / ".codex"


def test_codex_home_respects_env(monkeypatch, tmp_path):
    custom = tmp_path / "codex"
    monkeypatch.setenv("CODEX_HOME", str(custom))
    assert codex_home() == custom


def test_render_codex_note_mentions_codex():
    note = render_codex_note()
    assert "Codex" in note
    assert "Claude" not in note
    assert "Cursor" not in note