from __future__ import annotations

from pathlib import Path

from .context_brief import build_context_brief, write_context_map
from .output_policy import POLICY_NAME
from .project import detect_project
from .session_state import load_checkpoint
from .surface_brief import build_surface_brief
from .utils import estimate_tokens


def build_session_gate(root: Path, *, include_surface: bool = False, brief_budget: int = 100) -> str:
    info = detect_project(root)
    checkpoint = load_checkpoint(root)
    parts: list[str] = [
        f"ContextGuard session gate ({POLICY_NAME}; project={info.kind}):",
        "Use capture for tests, builds, logs, diffs, and broad search; inspect 1-4 files; expand archives only for missing evidence.",
        "Reuse unchanged reads and passing validation. Preserve correctness, security, and exact failure evidence.",
        "Output: no routine narration; final answer is changed files, validation, and real risks unless the user asks for detail.",
    ]
    brief, context_map = build_context_brief(root, budget_tokens=brief_budget)
    write_context_map(root, context_map)
    parts.append(brief)
    if include_surface:
        surface = build_surface_brief(root=root, budget_tokens=350)
        parts.append(surface)
    dynamic: list[str] = []
    objective = checkpoint.get("current_objective")
    if objective:
        dynamic.append(f"objective={objective}")
    if dynamic:
        parts.append("ContextGuard dynamic session state:")
        parts.extend(dynamic)
    text = "\n".join(part for part in parts if part)
    while estimate_tokens(text) > 360 and len(parts) > 3:
        parts.pop(-2)
        text = "\n".join(parts)
    return text
