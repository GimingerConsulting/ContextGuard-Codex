from __future__ import annotations

import os
from pathlib import Path


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def render_codex_note() -> str:
    return "ContextGuard: Codex-native plugin with project capture runner and lifecycle hooks."