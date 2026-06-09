from __future__ import annotations

from pathlib import Path

from .task_classifier import classify_task
from .utils import estimate_tokens


def build_capsule(root: Path, prompt: str, token_limit: int = 400) -> str:
    result = classify_task(root, prompt)
    if result["confidence"] == "low":
        text = (
            "ContextGuard task capsule: low classification confidence. "
            "Start with targeted search, symbol/range inspection and automatic context escalation when needed."
        )
    else:
        files = ", ".join(result["likely_files"][:4]) or "none"
        symbols = ", ".join(
            f"{item['name']}@{item['path']}:{item['line']}"
            for item in result.get("likely_symbols", [])[:2]
        ) or "none"
        tests = ", ".join(result.get("relevant_tests", [])[:3]) or "none"
        text = (
            "ContextGuard capsule: "
            f"confidence={result['confidence']}; "
            f"files={files}; "
            f"symbols={symbols}; "
            f"tests={tests}; "
            "start scoped; expand if needed."
        )
    while estimate_tokens(text) > token_limit and "\n-" in text:
        text = "\n".join(text.splitlines()[:-1])
    return text
