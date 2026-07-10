#!/usr/bin/env python3
"""Build a clean Codex marketplace release bundle for ContextGuard."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parent

IGNORE = shutil.ignore_patterns(
    ".git",
    ".DS_Store",
    ".pytest_cache",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".contextguard",
    "build",
    "dist",
    "*.egg-info",
    ".venv",
    "uv.lock",
    "changy.md",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pyproject_version() -> str:
    text = (PLUGIN_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("version not found in pyproject.toml")


def copy_plugin(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(PLUGIN_ROOT, destination, ignore=IGNORE)


def stamp_plugin_manifest(plugin_dir: Path, *, base_version: str, codex_version: str) -> None:
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = codex_version
    manifest["description"] = (
        "Codex-native context optimization: capture runner, session gate, family codecs, "
        "lifetime savings, worker-risk lock, and adaptive evidence compaction."
    )
    manifest["interface"]["shortDescription"] = "Codex context savings with lifetime reporting"
    manifest["interface"]["longDescription"] = (
        "Reduce unnecessary Codex context usage through local project intelligence, bounded inspect, "
        "capture-runner protection, session gate, doc-family codecs, lifetime/session cost reporting, "
        "and adaptive evidence compaction for noisy tool output."
    )
    manifest["interface"]["defaultPrompt"] = [
        "Run ContextGuard setup and verify this project.",
        "Show my ContextGuard lifetime savings.",
        "Show my ContextGuard session cost for this thread.",
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    release_meta = {
        "base_version": base_version,
        "codex_version": codex_version,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "plugin_sha256": sha256_file(manifest_path),
        "hooks_sha256": sha256_file(plugin_dir / "hooks" / "hooks.json"),
    }
    (plugin_dir / ".codex-plugin" / "release.json").write_text(
        json.dumps(release_meta, indent=2) + "\n",
        encoding="utf-8",
    )


def build_marketplace_bundle(bundle_root: Path, plugin_dir: Path) -> None:
    agents = bundle_root / ".agents" / "plugins"
    agents.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / ".agents" / "plugins" / "marketplace.json", agents / "marketplace.json")
    if (bundle_root / "contextguard").exists():
        shutil.rmtree(bundle_root / "contextguard")
    shutil.copytree(plugin_dir, bundle_root / "contextguard")


def run_validation(plugin_dir: Path) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=plugin_dir,
        text=True,
        capture_output=True,
    )
    acceptance_output = plugin_dir / "benchmarks" / "results" / "install-acceptance-release.json"
    acceptance_proc = subprocess.run(
        [
            sys.executable,
            str(plugin_dir / "benchmarks" / "install_acceptance.py"),
            "--output",
            str(acceptance_output),
            "--timing-samples",
            "1",
        ],
        cwd=plugin_dir,
        text=True,
        capture_output=True,
        env={
            **dict(__import__("os").environ),
            "PYTHONPATH": str(plugin_dir),
        },
    )
    acceptance = {}
    if acceptance_output.exists():
        acceptance = json.loads(acceptance_output.read_text(encoding="utf-8"))
    return {
        "pytest_exit_code": proc.returncode,
        "pytest_tail": "\n".join(proc.stdout.splitlines()[-3:]),
        "acceptance_exit_code": acceptance_proc.returncode,
        "acceptance_accepted": acceptance.get("accepted"),
        "acceptance_output": str(acceptance_output),
    }


def write_install_manifest(dist_root: Path, *, codex_version: str, bundle_root: Path, plugin_dir: Path) -> Path:
    manifest = {
        "product": "ContextGuard",
        "codex_version": codex_version,
        "bundle_root": str(bundle_root),
        "plugin_root": str(plugin_dir),
        "install_local_codex": [
            f'codex plugin marketplace add "{bundle_root}"',
            "codex plugin remove contextguard@contextguard || true",
            "codex plugin add contextguard@contextguard --json",
            "codex plugin list | rg contextguard",
        ],
        "install_from_github_after_push": [
            "codex plugin marketplace upgrade contextguard",
            "codex plugin remove contextguard@contextguard || true",
            "codex plugin add contextguard@contextguard --json",
        ],
        "smoke_test_in_new_thread": [
            "$contextguard-setup",
            "$contextguard-status",
            "$contextguard-lifetime-savings",
            "Run one noisy command through .contextguard/bin/contextguard capture -- <command>",
            "$contextguard-report",
            "Open /hooks and trust updated ContextGuard hooks if hashes changed",
        ],
        "live_ab_after_quota_reset": [
            "python3 benchmarks/real_codex_power_user_ab.py --run",
            "python3 benchmarks/power_user_scale_projection.py",
        ],
    }
    path = dist_root / f"RELEASE-{codex_version}.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=PLUGIN_ROOT / "dist")
    args = parser.parse_args(argv)

    base_version = read_pyproject_version()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    codex_version = f"{base_version}+codex.{stamp}"

    dist_root = args.output_dir
    dist_root.mkdir(parents=True, exist_ok=True)
    plugin_dir = dist_root / f"contextguard-{codex_version}"
    bundle_root = dist_root / f"marketplace-bundle-{codex_version}"

    copy_plugin(plugin_dir)
    stamp_plugin_manifest(plugin_dir, base_version=base_version, codex_version=codex_version)
    build_marketplace_bundle(bundle_root, plugin_dir)

    validation = {"skipped": True}
    if not args.skip_tests:
        validation = run_validation(plugin_dir)
        if validation["pytest_exit_code"] != 0:
            print(validation, file=sys.stderr)
            return validation["pytest_exit_code"]
        if validation["acceptance_exit_code"] != 0 or not validation.get("acceptance_accepted"):
            print(validation, file=sys.stderr)
            return 1

    release_manifest = write_install_manifest(
        dist_root,
        codex_version=codex_version,
        bundle_root=bundle_root,
        plugin_dir=plugin_dir,
    )
    summary = {
        "codex_version": codex_version,
        "plugin_dir": str(plugin_dir),
        "bundle_root": str(bundle_root),
        "release_manifest": str(release_manifest),
        "validation": validation,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())