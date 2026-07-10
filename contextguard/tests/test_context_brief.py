from pathlib import Path

from contextguard.context_brief import build_context_brief, build_context_map, expand_context


def test_context_map_includes_docs(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n\nSystem overview.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")

    context_map = build_context_map(tmp_path)
    paths = {item["path"] for item in context_map["files"]}
    assert "docs/ARCHITECTURE.md" in paths
    assert "README.md" in paths


def test_expand_context_verifies_sha(tmp_path: Path):
    doc = tmp_path / "docs" / "PRD.md"
    doc.parent.mkdir()
    doc.write_text("Product requirements.\n", encoding="utf-8")
    context_map = build_context_map(tmp_path)
    entry = next(item for item in context_map["files"] if item["path"] == "docs/PRD.md")

    ok = expand_context(tmp_path, "docs/PRD.md", expected_sha=str(entry["sha256"]))
    bad = expand_context(tmp_path, "docs/PRD.md", expected_sha="deadbeef")

    assert ok["ok"] is True
    assert "Product requirements" in ok["content"]
    assert bad["ok"] is False
    assert bad["error"] == "sha_mismatch"


def test_context_brief_respects_budget(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    for index in range(10):
        (tmp_path / "docs" / f"DOC_{index}.md").write_text("x" * 400 + "\n", encoding="utf-8")
    brief, _ = build_context_brief(tmp_path, budget_tokens=120)
    assert "context brief" in brief
    assert len(brief) < 2000