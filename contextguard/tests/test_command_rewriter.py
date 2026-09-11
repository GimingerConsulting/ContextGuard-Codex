from pathlib import Path
import shlex

from contextguard.command_rewriter import rewrite_for_capture, rewrite_for_inspect


def test_multi_source_cat_is_not_rewritten_to_lossy_outlines(tmp_path: Path):
    (tmp_path / "a.py").write_text("a=1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b=2\n", encoding="utf-8")

    rewritten = rewrite_for_inspect("cat a.py b.py", tmp_path)

    assert rewritten is None


def test_rewrite_single_whole_file_read_to_snapshot(tmp_path: Path):
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    assert "snapshot app.py" in rewrite_for_inspect("cat app.py", tmp_path)
    assert "snapshot app.py" in rewrite_for_inspect("nl -ba app.py", tmp_path)


def test_rewrite_codex_shell_envelope_to_capture_without_changing_inner_command(tmp_path: Path):
    command = "/bin/zsh -lc 'python3 -m pytest -q && git diff --check'"

    rewritten = rewrite_for_capture(command, Path("/plugin/scripts/contextguard"))

    assert rewritten is not None
    assert rewritten.startswith("/plugin/scripts/contextguard capture --")
    assert shlex.quote(command) in rewritten
