from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import database_path, state_dir
from .documentation import render_agents, write_managed_docs
from .hook_diagnostics import hook_status, observed_hooks
from .index import refresh_index
from .large_file import summarize_large_file
from .metrics import report as metrics_report
from .output_capture import capture
from .output_policy import POLICY_NAME
from .onboarding import initialize_project
from .project import detect_project
from .project_runner import install_project_runner, project_runner_ready, runner_path
from .repo_map import detect_repo_facts
from .session_state import load_session_state
from .database import connect, increment
from .source_inspector import InspectionError, inspect_sources


def init_project(args: argparse.Namespace) -> int:
    result = initialize_project(Path(args.path) if args.path else None)
    print("ContextGuard initialized")
    print(f"project: {result.project.root}")
    print(f"kind: {result.project.kind}")
    print(f"files_indexed: {result.files_indexed}")
    print(f"changed_docs: {', '.join(result.changed_docs) or 'none'}")
    return 0


def setup(args: argparse.Namespace) -> int:
    result = initialize_project(Path(args.path) if args.path else None)
    hooks = observed_hooks(result.project.root)
    readiness = hook_status(hooks)
    print("ContextGuard setup complete")
    print("Project: initialized")
    print(f"Project kind: {result.project.kind}")
    print(f"Files indexed: {result.files_indexed}")
    print("Execution protection: ready")
    print(f"Project runner: {runner_path(result.project.root)}")
    print("Noisy commands are compacted before stdout reaches Codex; this works without hook output replacement.")
    if readiness == "observed":
        print("Hook status: observed")
        print(f"Observed hooks: {', '.join(sorted(hooks))}")
        print("ContextGuard is ready for normal Codex use.")
    elif hooks:
        print("Hook status: partially observed")
        print(f"Observed hooks: {', '.join(sorted(hooks))}")
        print("Run one normal Codex tool command, then run $contextguard-status to verify tool hooks.")
    else:
        print("Hook status: not yet observed")
        print("Open /hooks in Codex, review and trust the ContextGuard hooks, then start a new thread.")
    return 0


def status(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    initialized = (state_dir(info.root) / "manifest.json").exists()
    metrics = metrics_report(info.root) if initialized else {}
    print(f"ContextGuard: {'active' if initialized else 'inactive'}")
    print(f"Project: {'initialized' if initialized else 'not initialized'}")
    print(f"Optimization: {POLICY_NAME}")
    print("Quality guard: enabled")
    print(f"Index: {'current' if initialized else 'missing'}")
    print(f"Large output protection: {'active' if initialized else 'inactive'}")
    print(f"Execution protection: {'ready' if initialized and project_runner_ready(info.root) else 'missing'}")
    if initialized:
        print(f"Project runner: {runner_path(info.root)}")
        session = load_session_state(info.root)
        session_metrics = session.get("metrics", {})
        print(f"Session commands tracked: {len(session.get('commands', []))}")
        print(f"Repeated reads detected: {session_metrics.get('repeated_reads_detected', 0)}")
        print(f"Command budget advice emitted: {session_metrics.get('budget_advice_emitted', 0)}")
    hooks = observed_hooks(info.root) if initialized else {}
    print(f"Hook status: {hook_status(hooks)}")
    if hooks:
        print(f"Observed hooks: {', '.join(sorted(hooks))}")
    print(f"Last refresh: {metrics.get('last_refresh', 'unknown')}")
    print(f"Current project files indexed: {metrics.get('files_indexed', 0)}")
    print(f"Current session commands intercepted: {metrics.get('commands_intercepted', 0)}")
    print(f"Lifetime estimated tokens saved: {metrics.get('estimated_tokens_saved', 0)}")
    print(f"Lifetime context reduction: {metrics.get('estimated_reduction_percent', 0)}%")
    print(f"Estimated net context reduction: {metrics.get('estimated_tokens_avoided', 0)} tokens (estimate)")
    return 0


def refresh(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    install_project_runner(info.root)
    stats = refresh_index(info.root)
    (state_dir(info.root) / "repo_map.json").write_text(
        json.dumps(detect_repo_facts(info.root), indent=2) + "\n",
        encoding="utf-8",
    )
    docs = write_managed_docs(info)
    conn = connect(database_path(info.root))
    conn.execute(
        "insert or replace into metrics(key, value) values('managed_policy_bytes', ?)",
        (len(render_agents(info).encode()),),
    )
    conn.commit()
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


def inspect(args: argparse.Namespace) -> int:
    try:
        data = inspect_sources(
            Path.cwd(),
            args.files,
            symbol=args.symbol,
            start_line=args.start_line,
            end_line=args.end_line,
        )
    except InspectionError as exc:
        payload = {
            "ok": False,
            "command": "inspect",
            "error": {"code": exc.code, "message": str(exc)},
        }
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        return 2
    print(json.dumps(data, separators=(",", ":"), sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contextguard")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("init", init_project), ("setup", setup), ("status", status), ("refresh", refresh), ("report", report)):
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
    p = sub.add_parser("inspect")
    p.add_argument("files", nargs="+")
    p.add_argument("--symbol")
    p.add_argument("--start-line", type=int)
    p.add_argument("--end-line", type=int)
    p.set_defaults(func=inspect)
    p = sub.add_parser("uninstall-project")
    p.add_argument("--path")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=uninstall_project)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
