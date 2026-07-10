from pathlib import Path

from contextguard.command_rewriter import rewrite_for_inspect


def test_rewrite_multi_source_cat_to_inspect(tmp_path: Path):
    (tmp_path / "a.py").write_text("a=1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b=2\n", encoding="utf-8")

    rewritten = rewrite_for_inspect("cat a.py b.py", tmp_path)

    assert rewritten is not None
    assert "inspect" in rewritten
    assert "a.py" in rewritten
    assert "b.py" in rewritten