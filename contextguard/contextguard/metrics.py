from __future__ import annotations

from pathlib import Path

from .config import database_path
from .database import connect
from .history_pack import archive_index_summary
from .ledger import ledger_summary
from .quota_proxy import quota_proxy_report
from .lifetime_savings import lifetime_savings_report
from .session_cost import session_cost_report


def report(root: Path) -> dict:
    conn = connect(database_path(root))
    metrics = dict(conn.execute("select key, value from metrics").fetchall())
    files = conn.execute("select count(*) from files").fetchone()[0]
    project = dict(conn.execute("select key, value from project").fetchall())
    commands = conn.execute("select count(*), coalesce(sum(stdout_bytes + stderr_bytes),0) from commands").fetchone()
    raw = max(int(commands[1] or 0), int(metrics.get("raw_output_bytes", 0)))
    compact = int(metrics.get("compact_output_bytes", 0))
    saved_bytes = max(0, raw - compact)
    reduction = round((saved_bytes / raw) * 100, 2) if raw else 0.0
    policy_bytes = int(metrics.get("managed_policy_bytes", 0))
    capsule_bytes = int(metrics.get("context_bytes_added", 0))
    estimated_overhead = policy_bytes + capsule_bytes
    return {
        "files_indexed": files,
        "last_refresh": project.get("last_refresh", "unknown"),
        "commands_intercepted": int(commands[0] or 0),
        "commands_rewritten": int(metrics.get("commands_rewritten", 0)),
        "raw_output_bytes": raw,
        "compact_output_bytes": compact,
        "estimated_saved_bytes": saved_bytes,
        "large_files_summarized": int(metrics.get("large_files_summarized", 0)),
        "cache_hits": int(metrics.get("cache_hits", 0)),
        "cache_misses": int(metrics.get("cache_misses", 0)),
        "repeated_reads_avoided": int(metrics.get("repeated_reads_avoided", 0)),
        "files_inspected": files,
        "tool_calls": int(commands[0] or 0),
        "full_file_reads_avoided": int(metrics.get("full_file_reads_avoided", 0)),
        "focused_tests_used": int(metrics.get("focused_tests_used", 0)),
        "index_refresh_duration_ms": int(metrics.get("index_refresh_duration_ms", 0)),
        "estimated_tokens_avoided": max(0, raw // 4 - estimated_overhead // 4),
        "estimated_tokens_saved": saved_bytes // 4,
        "estimated_reduction_percent": reduction,
        "estimated_contextguard_overhead_tokens": estimated_overhead // 4,
        "managed_policy_bytes": policy_bytes,
        "injected_capsule_bytes": capsule_bytes,
        "net_estimated_reduction_tokens": max(0, saved_bytes // 4 - estimated_overhead // 4),
        "ledger": ledger_summary(root),
        "archive_index": archive_index_summary(root),
        "quota_proxy": quota_proxy_report(root),
        "session_cost": session_cost_report(root),
        "lifetime_savings": lifetime_savings_report(root),
    }
