from __future__ import annotations

from pathlib import Path

from .context_brief import build_context_brief, write_context_map
from .context_capsule import build_session_capsule
from .doc_families import render_doc_families_brief
from .hook_diagnostics import hook_status, observed_hooks
from .host_adapter import render_codex_note
from .host_policy import inspect_first_directive, render_host_enforcement_note
from .ledger import record_ledger
from .output_policy import POLICY_NAME
from .project import detect_project
from .session_state import load_checkpoint
from .surface_brief import build_surface_brief
from .utils import estimate_tokens


def build_session_gate(root: Path, *, include_surface: bool = False, brief_budget: int = 450) -> str:
    info = detect_project(root)
    checkpoint = load_checkpoint(root)
    parts: list[str] = [
        f"ContextGuard session gate ({POLICY_NAME}):",
        f"project={info.kind}",
        render_codex_note(),
        inspect_first_directive(),
        (
            "Execution: use capture for noisy commands; inspect for 1-4 source or structured files; "
            "expand exact docs only when the brief is insufficient."
        ),
    ]
    session_capsule = build_session_capsule(root, token_limit=250)
    families = render_doc_families_brief(root)
    if families:
        parts.append(families)
        record_ledger(root, "brief", bytes_added=len(families.encode()), label="doc_families")
    brief, context_map = build_context_brief(root, budget_tokens=brief_budget)
    write_context_map(root, context_map)
    parts.append(brief)
    if include_surface:
        surface = build_surface_brief(root=root, budget_tokens=350)
        parts.append(surface)
    parts.append(render_host_enforcement_note(hooks_observed=hook_status(observed_hooks(root)) == "observed"))
    dynamic: list[str] = []
    objective = checkpoint.get("current_objective")
    if objective:
        dynamic.append(f"objective={objective}")
    if session_capsule:
        dynamic.append(session_capsule)
        record_ledger(root, "capsule", bytes_added=len(session_capsule.encode()), label="session_capsule")
    if dynamic:
        parts.append("ContextGuard dynamic session state:")
        parts.extend(dynamic)
    text = "\n".join(part for part in parts if part)
    while estimate_tokens(text) > 1400 and len(parts) > 3:
        parts.pop(-2)
        text = "\n".join(parts)
    return text
