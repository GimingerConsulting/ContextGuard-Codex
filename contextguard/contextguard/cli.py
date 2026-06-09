from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import database_path, state_dir
from .documentation import write_managed_docs
from .index import refresh_index
from .large_file import summarize_large_file
from .metrics import report as metrics_report
from .output_capture import capture
from .project import detect_project
from .repo_map import detect_repo_facts
from .database import connect, increment


def init_project(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    for name in ("cache", "sessions", "reports", "tmp"):
        (state_dir(info.root) / name).mkdir(parents=True, exist_ok=True)
    index_stats = refresh_index(info.root)
    (state_dir(info.root) / "repo_map.json").write_text(
        json.dumps(detect_repo_facts(info.root), indent=2) + "\n",
        encoding="utf-8",
    )
    changed_docs = write_managed_docs(info)
    manifest = {
        "initialized_at": datetime.now(timezone.utc).isoformat(),
        "project_root": info.root.as_posix(),
        "project_kind": info.kind,
        "policy": "Adaptive Maximum Savings",
        "database": database_path(info.root).as_posix(),
    }
    (state_dir(info.root) / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("ContextGuard initialized")
    print(f"project: {info.root}")
    print(f"kind: {info.kind}")
    print(f"files_indexed: {index_stats['files_indexed']}")
    print(f"changed_docs: {', '.join(changed_docs) or 'none'}")
    return 0


def status(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    initialized = (state_dir(info.root) / "manifest.json").exists()
    metrics = metrics_report(info.root) if initialized else {}
    print(f"ContextGuard: {'active' if initialized else 'inactive'}")
    print(f"Project: {'initialized' if initialized else 'not initialized'}")
    print("Optimization: Adaptive Maximum Savings")
    print("Quality guard: enabled")
    print(f"Index: {'current' if initialized else 'missing'}")
    print(f"Large output protection: {'active' if initialized else 'inactive'}")
    print(f"Last refresh: {metrics.get('last_refresh', 'unknown')}")
    print(f"Current project files indexed: {metrics.get('files_indexed', 0)}")
    print(f"Current session commands intercepted: {metrics.get('commands_intercepted', 0)}")
    print(f"Lifetime estimated tokens saved: {metrics.get('estimated_tokens_saved', 0)}")
    print(f"Lifetime context reduction: {metrics.get('estimated_reduction_percent', 0)}%")
    print(f"Estimated net context reduction: {metrics.get('estimated_tokens_avoided', 0)} tokens (estimate)")
    return 0


def refresh(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    stats = refresh_index(info.root)
    (state_dir(info.root) / "repo_map.json").write_text(
        json.dumps(detect_repo_facts(info.root), indent=2) + "\n",
        encoding="utf-8",
    )
    docs = write_managed_docs(info)
    print("ContextGuard refresh complete")
    print(json.dumps({"index": stats, "managed_docs_changed": docs}, indent=2))
    return 0


def report(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = metrics_report(info.root)
    print("ContextGuard savings report")
    for key, value in data.items():
        suffix = " (estimate)" if "tokens" in key else ""
        print(f"{key}: {value}{suffix}")
    return 0


def uninstall_project(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    print("ContextGuard project files:")
    print(f"- {state_dir(info.root)}")
    print("- ContextGuard-managed sections in AGENTS.md and docs/*.md")
    if args.yes:
        import shutil

        shutil.rmtree(state_dir(info.root), ignore_errors=True)
        print("Removed .contextguard state. Managed Markdown sections were preserved.")
    else:
        print("Re-run with --yes to remove .contextguard state.")
    return 0


def large_file(args: argparse.Namespace) -> int:
    info = detect_project()
    data = summarize_large_file(
        Path(args.file),
        contains=args.contains,
        limit=args.limit,
        key=args.key,
        value=args.value,
        before=args.before,
        after=args.after,
        lines=args.lines,
        records=args.records,
    )
    conn = connect(database_path(info.root))
    increment(conn, "large_files_summarized", 1)
    print(json.dumps(data, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contextguard")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("init", init_project), ("status", status), ("refresh", refresh), ("report", report)):
        p = sub.add_parser(name)
        p.add_argument("--path")
        p.set_defaults(func=fn)
    p = sub.add_parser("capture")
    p.add_argument("command_argv", nargs=argparse.REMAINDER)
    def run_capture(a: argparse.Namespace) -> int:
        command = a.command_argv[1:] if a.command_argv[:1] == ["--"] else a.command_argv
        if not command:
            print("contextguard capture requires a command after --", file=sys.stderr)
            return 2
        return capture(Path.cwd(), command)

    p.set_defaults(func=run_capture)
    p = sub.add_parser("large-file")
    p.add_argument("file")
    p.add_argument("--contains")
    p.add_argument("--key")
    p.add_argument("--value")
    p.add_argument("--before", type=int, default=0)
    p.add_argument("--after", type=int, default=0)
    p.add_argument("--lines")
    p.add_argument("--records")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=large_file)
    p = sub.add_parser("uninstall-project")
    p.add_argument("--path")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=uninstall_project)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
