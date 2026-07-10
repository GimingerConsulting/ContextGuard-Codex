from __future__ import annotations

from pathlib import Path

from .host_adapter import codex_home
from .ledger import record_ledger
from .utils import estimate_tokens


DEFAULT_BUDGET_TOKENS = 500


def _safe_list(path: Path, *, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    try:
        return sorted(item.name for item in path.iterdir() if not item.name.startswith("."))[:limit]
    except OSError:
        return []


def _skill_summaries(skills_root: Path, *, limit: int = 12) -> list[str]:
    if not skills_root.exists():
        return []
    lines: list[str] = []
    for skill_dir in sorted(skills_root.iterdir())[:limit]:
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        preview = ""
        tokens_est = 0
        if skill_md.is_file():
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
                preview = text.splitlines()[0][:120] if text else ""
                tokens_est = estimate_tokens(text[:8000])
            except OSError:
                preview = ""
        lines.append(
            f"- skill:{skill_dir.name} tokens~{tokens_est} preview={preview or '(no SKILL.md)'}"
        )
    return lines


def build_surface_brief(*, budget_tokens: int = DEFAULT_BUDGET_TOKENS, root: Path | None = None) -> str:
    surface_root = codex_home()
    lines = ["ContextGuard Codex surface brief (expand exact surface only when needed):"]
    skills = _skill_summaries(surface_root / "skills")
    memories = _safe_list(surface_root / "memories")
    plugins = _safe_list(surface_root / "plugins" / "cache")
    agents = _safe_list(surface_root / "agents")
    if skills:
        lines.append("skills:")
        lines.extend(skills)
    if memories:
        lines.append("memories: " + ", ".join(memories))
    if plugins:
        lines.append("plugins: " + ", ".join(plugins))
    if agents:
        lines.append("agents: " + ", ".join(agents))
    if len(lines) == 1:
        lines.append("- no ~/.codex surfaces detected")
    text = "\n".join(lines)
    while estimate_tokens(text) > budget_tokens and len(lines) > 2:
        lines.pop()
        text = "\n".join(lines) + "\n- ... additional Codex surfaces truncated"
    if root is not None:
        record_ledger(root, "surface_brief", bytes_added=len(text.encode()), label="codex_surface")
    return text