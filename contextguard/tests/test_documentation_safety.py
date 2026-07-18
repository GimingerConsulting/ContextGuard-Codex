from pathlib import Path

from contextguard.documentation import replace_managed_section, render_agents
from contextguard.project import ProjectInfo
from contextguard.config import MANAGED_BEGIN, MANAGED_END


ROOT = Path(__file__).resolve().parents[1]


def test_existing_agents_preservation_and_backup(tmp_path: Path):
    path = tmp_path / "AGENTS.md"
    path.write_text("# User\n\nKeep this.\n")
    changed = replace_managed_section(path, "Project Instructions", "managed")
    assert changed
    text = path.read_text()
    assert "Keep this." in text
    assert MANAGED_BEGIN in text and MANAGED_END in text
    assert list(tmp_path.glob("AGENTS.md.contextguard-backup-*"))


def test_managed_section_replacement(tmp_path: Path):
    path = tmp_path / "AGENTS.md"
    replace_managed_section(path, "Project Instructions", "first")
    replace_managed_section(path, "Project Instructions", "second")
    text = path.read_text()
    assert "second" in text
    assert "first" not in text


def test_hooks_json_uses_current_codex_nested_schema():
    import json

    path = Path(__file__).resolve().parents[1] / "hooks" / "hooks.json"
    hooks = json.loads(path.read_text())["hooks"]
    handler = hooks["PreToolUse"][0]["hooks"][0]
    assert hooks["PreToolUse"][0]["matcher"] == ".*"
    assert handler["type"] == "command"
    assert handler["command"] == (
        'test ! -f "$PLUGIN_ROOT/hooks/pre_tool_use.py" || '
        'python3 "$PLUGIN_ROOT/hooks/pre_tool_use.py"'
    )


def test_marketplace_readme_documents_complete_safe_onboarding():
    readme = (ROOT / "README.md").read_text()

    assert "codex plugin marketplace add GimingerConsulting/ContextGuard" in readme
    assert "/hooks" in readme
    assert "$contextguard-setup" in readme
    assert "new thread" in readme.lower()
    assert "smoke test" in readme.lower()


def test_setup_skill_uses_bundled_runner_and_manifest_promotes_setup():
    import json

    skill = (ROOT / "skills" / "contextguard-setup" / "SKILL.md").read_text()
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())

    assert '$PLUGIN_ROOT/scripts/contextguard" setup' in skill
    assert any("setup" in prompt.lower() for prompt in manifest["interface"]["defaultPrompt"])


def test_all_command_skills_use_the_bundled_runner():
    for name in ("init", "refresh", "report", "status", "uninstall-project"):
        skill = (ROOT / "skills" / f"contextguard-{name}" / "SKILL.md").read_text()
        assert '"$PLUGIN_ROOT/scripts/contextguard"' in skill


def test_managed_policy_keeps_optimization_transparent(tmp_path: Path):
    policy = render_agents(
        ProjectInfo(root=tmp_path, kind="existing", is_git=False, is_monorepo=False)
    )

    assert "Use normal shell/source commands" in policy
    assert "Hooks optimize large output automatically" in policy
    assert "never call ContextGuard commands" in policy
    assert "Stop once evidence is sufficient" in policy
    assert len(policy.encode()) < 1400


def test_public_readme_documents_license_terms():
    readme = (ROOT / "README.md").read_text()

    required = [
        "## License",
        "source-available",
        "PolyForm Noncommercial License 1.0.0",
        "Commercial Licensing",
        "commercial license",
    ]

    for phrase in required:
        assert phrase in readme


def test_public_readme_documents_install_usage_costs_and_limits():
    readme = (ROOT / "README.md").read_text()

    required = [
        "## Install and update",
        "## Initialize a project",
        "contextguard init --path .",
        "contextguard session-cost",
        "contextguard lifetime-savings",
        "## Known limitations",
        "not verified Codex server-side billing",
        "Small commands can cost slightly more than they save",
        "Existing projects keep user-authored AGENTS.md content",
    ]

    for phrase in required:
        assert phrase in readme
