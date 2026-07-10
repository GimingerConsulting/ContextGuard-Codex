#!/usr/bin/env python3
"""Install ContextGuard 0.9.x from an immutable local marketplace bundle.

Pins Codex to the dist bundle instead of the git repo so Codex restarts cannot
downgrade to the older GitHub marketplace version (currently 0.5.1 on main).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parent
CODEX_HOME = Path.home() / ".codex"
CONFIG = CODEX_HOME / "config.toml"
CACHE_ROOT = CODEX_HOME / "plugins" / "cache" / "contextguard" / "contextguard"


def set_local_marketplace_source(bundle_root: Path) -> None:
    text = CONFIG.read_text(encoding="utf-8")
    block = (
        "[marketplaces.contextguard]\n"
        f'last_updated = "{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}"\n'
        'source_type = "local"\n'
        f'source = "{bundle_root.as_posix()}"\n'
    )
    if "[marketplaces.contextguard]" in text:
        text = re.sub(
            r"\[marketplaces\.contextguard\][^\[]*",
            block,
            text,
            count=1,
        )
    else:
        text = text.rstrip() + "\n\n" + block
    CONFIG.write_text(text, encoding="utf-8")


def run_codex(args: list[str]) -> dict | str | None:
    proc = subprocess.run(["codex", *args], text=True, capture_output=True)
    if proc.stdout.strip():
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    return {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}


def build_bundle(*, skip_tests: bool) -> dict:
    cmd = [sys.executable, str(PLUGIN_ROOT / "scripts" / "build_marketplace_release.py")]
    if skip_tests:
        cmd.append("--skip-tests")
    proc = subprocess.run(cmd, cwd=PLUGIN_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    dist_root = PLUGIN_ROOT / "dist"
    releases = sorted(dist_root.glob("RELEASE-*.json"))
    if not releases:
        raise RuntimeError("release manifest missing after build")
    manifest = json.loads(releases[-1].read_text(encoding="utf-8"))
    return manifest


def install_from_bundle(bundle_root: Path) -> dict:
    run_codex(["plugin", "marketplace", "remove", "contextguard"])
    run_codex(["plugin", "marketplace", "add", str(bundle_root)])
    set_local_marketplace_source(bundle_root)
    run_codex(["plugin", "remove", "contextguard@contextguard"])
    return run_codex(["plugin", "add", "contextguard@contextguard", "--json"])


def main(argv: list[str] | None = None) -> int:
    skip_tests = "--skip-tests" in (argv or sys.argv[1:])
    manifest = build_bundle(skip_tests=skip_tests)
    bundle_root = Path(manifest["bundle_root"])
    plugin_root = Path(manifest["plugin_root"])
    version = manifest["codex_version"]

    install = install_from_bundle(bundle_root)
    cache_versions = sorted(p.name for p in CACHE_ROOT.iterdir()) if CACHE_ROOT.exists() else []
    plugin_manifest = json.loads((bundle_root / "contextguard" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    summary = {
        "installed_version": plugin_manifest.get("version"),
        "expected_version": version,
        "marketplace_source": str(bundle_root),
        "plugin_root": str(plugin_root),
        "cache_versions": cache_versions,
        "install_result": install,
        "verify": {
            "has_lifetime_savings": (plugin_root / "contextguard" / "lifetime_savings.py").exists(),
            "has_family_codec": (plugin_root / "contextguard" / "family_codec.py").exists(),
            "github_main_still_older": (
                "GitHub main is still 0.5.1 until you commit and push 0.9.0. "
                "This installer pins Codex to the local dist bundle to avoid downgrade on restart."
            ),
        },
    }
    print(json.dumps(summary, indent=2))

    if plugin_manifest.get("version") != version:
        return 1
    if version not in cache_versions:
        return 1
    if not summary["verify"]["has_lifetime_savings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())