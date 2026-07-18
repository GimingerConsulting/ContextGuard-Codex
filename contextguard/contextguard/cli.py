from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from .config import database_path, state_dir
from .documentation import render_agents, write_managed_docs
from .hook_diagnostics import hook_status, observed_hooks
from .index import refresh_index
from .large_file import summarize_large_file
from .metrics import report as metrics_report
from .output_capture import capture
from .output_retrieval import retrieve_output
from .output_policy import POLICY_NAME
from .onboarding import initialize_project
from .project import detect_project
from .project_runner import install_project_runner, project_runner_ready, runner_path
from .repo_map import detect_repo_facts
from .session_state import load_session_state, record_working_set
from .database import connect, increment
from .source_inspector import InspectionError, inspect_sources
from .context_brief import build_context_brief, expand_context, write_context_map
from .session_gate import build_session_gate
from .evidence_expand import expand_from_evidence, list_evidence_entries, write_evidence_index
from .host_adapter import render_codex_note
from .host_policy import render_host_enforcement_note
from .history_pack import archive_index_summary
from .lifetime_savings import lifetime_savings_report
from .quota_proxy import quota_proxy_report
from .cross_session import load_cross_session_summary, render_cross_session_brief
from .session_cost import session_cost_report
from .ledger import ledger_summary
from .task_evidence import build_task_evidence
from .snapshot_store import snapshot_source
from .budget_enforcer import evaluate_budget, render_budget_feedback


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
        print(f"Routing locked: {session.get('routing_locked', False)}")
        ledger = ledger_summary(info.root)
        print(f"Ledger events: {sum(ledger.get('counts', {}).values())}")
        hooks = observed_hooks(info.root)
        print(render_codex_note())
        print(render_host_enforcement_note(hooks_observed=hook_status(hooks) == "observed"))
        session_cost_data = metrics.get("session_cost") or {}
        print(
            "Session net tokens saved (estimate): "
            f"{session_cost_data.get('session_net_tokens_saved_estimate', 0)}"
        )
        print(
            "Session API savings (estimate): "
            f"${session_cost_data.get('estimated_session_api_savings_usd', 0)}"
        )
        lifetime = metrics.get("lifetime_savings") or {}
        print(f"Lifetime sessions: {lifetime.get('lifetime_sessions', 0)}")
        print(
            "Lifetime net tokens saved (estimate): "
            f"{lifetime.get('lifetime_combined_net_tokens_saved_estimate', 0)}"
        )
        print(
            "Lifetime API savings (estimate): "
            f"${lifetime.get('estimated_lifetime_api_savings_usd', 0)}"
        )
        evidence_entries = list_evidence_entries(info.root)
        if evidence_entries:
            print(f"Evidence entries: {len(evidence_entries)}")
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


def _print_metric_block(title: str, data: dict[str, object]) -> None:
    print(title)
    for key, value in data.items():
        suffix = " (estimate)" if "tokens" in key else ""
        print(f"{key}: {value}{suffix}")


def report(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = metrics_report(info.root)
    print("ContextGuard savings report")
    for key, value in data.items():
        if key in {"session_cost", "lifetime_savings", "ledger", "archive_index", "quota_proxy"}:
            continue
        suffix = " (estimate)" if "tokens" in key else ""
        print(f"{key}: {value}{suffix}")
    session_cost_data = data.get("session_cost")
    if isinstance(session_cost_data, dict):
        print()
        _print_metric_block("Session cost (current session):", session_cost_data)
    lifetime = data.get("lifetime_savings")
    if isinstance(lifetime, dict):
        print()
        _print_metric_block("Lifetime savings (all sessions):", lifetime)
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


def gate(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    text = build_session_gate(info.root, include_surface=not args.no_surface)
    print(text)
    return 0


def brief(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    text, context_map = build_context_brief(info.root, budget_tokens=args.budget)
    write_context_map(info.root, context_map)
    print(text)
    return 0


def expand(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = expand_context(info.root, args.file, expected_sha=args.sha)
    print(json.dumps(data if not data.get("ok") else {key: data[key] for key in data if key != "content"}, indent=2))
    if data.get("ok") and args.show_content:
        print(data["content"])
    return 0 if data.get("ok") else 2


def session_cost(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = session_cost_report(info.root)
    _print_metric_block("ContextGuard session cost (current session):", data)
    return 0


def lifetime_savings(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = lifetime_savings_report(info.root)
    _print_metric_block("ContextGuard lifetime savings (all sessions):", data)
    return 0


def quota_proxy(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = quota_proxy_report(info.root)
    _print_metric_block("ContextGuard quota proxy (API-cost estimate):", data)
    return 0


def archive_index(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = archive_index_summary(info.root)
    print(json.dumps(data, indent=2))
    return 0


def cross_session(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    if args.json:
        print(json.dumps(load_cross_session_summary(info.root), indent=2))
    else:
        text = render_cross_session_brief(info.root, token_limit=args.limit)
        print(text or "No prior-session summary stored yet.")
    return 0


def expand_evidence(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    data = expand_from_evidence(info.root, args.fingerprint)
    print(json.dumps(data, indent=2, default=str))
    write_evidence_index(info.root)
    return 0 if data.get("ok") else 2


def get_output(args: argparse.Namespace) -> int:
    line_range = None
    if args.lines:
        try:
            start_text, end_text = args.lines.split(":", 1)
            line_range = (int(start_text), int(end_text))
        except (ValueError, TypeError):
            print(json.dumps({"ok": False, "error": "lines must be START:END"}, sort_keys=True))
            return 2
    try:
        data = retrieve_output(
            Path.cwd(),
            args.handle,
            lines=line_range,
            pattern=args.grep,
            stream=args.stream,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(data, separators=(",", ":"), sort_keys=True))
    return 0


def inspect(args: argparse.Namespace) -> int:
    command_parts = ["contextguard", "inspect", *args.files]
    if args.symbol:
        command_parts.extend(["--symbol", args.symbol])
    if args.start_line is not None:
        command_parts.extend(["--start-line", str(args.start_line)])
    if args.end_line is not None:
        command_parts.extend(["--end-line", str(args.end_line)])
    budget = evaluate_budget(Path.cwd(), shlex.join(command_parts))
    if budget.action == "deny":
        print(render_budget_feedback(budget))
        return 2
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
    from .ledger import record_ledger

    rendered = json.dumps(data, separators=(",", ":"), sort_keys=True)
    record_ledger(Path.cwd(), "inspect", bytes_added=len(rendered.encode()), label=",".join(args.files[:4]))
    print(rendered)
    return 0


def orient(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    text = build_task_evidence(info.root, args.query, token_limit=args.budget)
    if text:
        record_working_set(info.root, text)
    print(text or "ContextGuard task evidence: no high-confidence packet; start with scoped search.")
    return 0


def snapshot(args: argparse.Namespace) -> int:
    info = detect_project(Path(args.path).resolve() if args.path else None)
    budget = evaluate_budget(info.root, shlex.join(["contextguard", "snapshot", args.file]))
    if budget.action == "deny":
        print(render_budget_feedback(budget))
        return 2
    try:
        result = snapshot_source(info.root, args.file)
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "file": args.file}, sort_keys=True))
        return 2
    print(result["rendered"], end="")
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
    p = sub.add_parser("get")
    p.add_argument("handle")
    selection = p.add_mutually_exclusive_group()
    selection.add_argument("--lines")
    selection.add_argument("--grep")
    p.add_argument("--stream", choices=("both", "stdout", "stderr"), default="both")
    p.set_defaults(func=get_output)
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
    p = sub.add_parser("gate")
    p.add_argument("--path")
    p.add_argument("--no-surface", action="store_true")
    p.set_defaults(func=gate)
    p = sub.add_parser("brief")
    p.add_argument("--path")
    p.add_argument("--budget", type=int, default=800)
    p.set_defaults(func=brief)
    p = sub.add_parser("expand")
    p.add_argument("file")
    p.add_argument("--path")
    p.add_argument("--sha")
    p.add_argument("--show-content", action="store_true")
    p.set_defaults(func=expand)
    p = sub.add_parser("session-cost")
    p.add_argument("--path")
    p.set_defaults(func=session_cost)
    p = sub.add_parser("lifetime-savings")
    p.add_argument("--path")
    p.set_defaults(func=lifetime_savings)
    p = sub.add_parser("quota-proxy")
    p.add_argument("--path")
    p.set_defaults(func=quota_proxy)
    p = sub.add_parser("archive-index")
    p.add_argument("--path")
    p.set_defaults(func=archive_index)
    p = sub.add_parser("cross-session")
    p.add_argument("--path")
    p.add_argument("--json", action="store_true")
    p.add_argument("--limit", type=int, default=400)
    p.set_defaults(func=cross_session)
    p = sub.add_parser("expand-evidence")
    p.add_argument("fingerprint")
    p.add_argument("--path")
    p.set_defaults(func=expand_evidence)
    p = sub.add_parser("inspect")
    p.add_argument("files", nargs="+")
    p.add_argument("--symbol")
    p.add_argument("--start-line", type=int)
    p.add_argument("--end-line", type=int)
    p.set_defaults(func=inspect)
    p = sub.add_parser("orient")
    p.add_argument("--query", required=True)
    p.add_argument("--path")
    p.add_argument("--budget", type=int, default=900)
    p.set_defaults(func=orient)
    p = sub.add_parser("snapshot")
    p.add_argument("file")
    p.add_argument("--path")
    p.set_defaults(func=snapshot)
    p = sub.add_parser("uninstall-project")
    p.add_argument("--path")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=uninstall_project)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
