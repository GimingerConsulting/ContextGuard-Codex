from contextguard.doc_families import render_doc_families_brief
from contextguard.family_codec import encode_family_entries, render_family_codec_brief


def test_encode_family_entries_marks_canonical_and_deltas():
    entries = [
        {"path": "docs/ARCHITECTURE.md", "sha256": "aaa", "tokens_est": 100},
        {"path": "docs/ARCHITECTURE_v2.md", "sha256": "bbb", "tokens_est": 140},
    ]
    lines = encode_family_entries("architecture", entries)
    assert any("canonical=docs/ARCHITECTURE.md" in line for line in lines)
    assert any("delta:docs/ARCHITECTURE_v2.md" in line for line in lines)
    assert any("Δtokens~+40" in line for line in lines)


def test_render_doc_families_brief_uses_codec_format(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    (tmp_path / "docs" / "ARCHITECTURE_v2.md").write_text("# Architecture v2\n", encoding="utf-8")
    brief = render_doc_families_brief(tmp_path)
    assert "family codec" in brief
    assert "canonical=docs/ARCHITECTURE.md" in brief


def test_render_family_codec_brief_truncates_at_budget():
    families = {
        f"family_{index}": [{"path": f"docs/{index}.md", "sha256": "abc", "tokens_est": 10}]
        for index in range(20)
    }
    brief = render_family_codec_brief(families, budget_lines=5)
    assert "truncated" in brief