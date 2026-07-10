from pathlib import Path

from contextguard.model_router import route_task


def test_bounded_feature_is_eligible_for_single_mini_worker(tmp_path: Path):
    result = route_task(
        tmp_path,
        "Implement the validated parser change in parser.py and add focused tests.",
        likely_files=["parser.py", "tests/test_parser.py"],
        confidence="high",
    )

    assert result["eligible"] is True
    assert result["agent"] == "contextguard-worker"
    assert result["model"] == "gpt-5.4-mini"
    assert result["max_workers"] == 1
    assert "final validation" in result["parent_responsibilities"]


def test_trivial_task_avoids_worker_handoff_overhead(tmp_path: Path):
    result = route_task(
        tmp_path,
        "Rename one constant.",
        likely_files=["constants.py"],
        confidence="high",
    )

    assert result["eligible"] is False
    assert result["reason"] == "handoff_overhead_exceeds_expected_savings"


def test_risky_or_ambiguous_task_stays_with_parent(tmp_path: Path):
    for prompt in (
        "Migrate the production authentication schema without data loss.",
        "Fix a concurrent payment race condition.",
        "Investigate an unclear security incident.",
    ):
        result = route_task(tmp_path, prompt, likely_files=[], confidence="low")
        assert result["eligible"] is False
        assert result["reason"] in {"high_risk_task", "insufficient_scope_confidence"}


def test_migration_file_in_scope_blocks_worker(tmp_path: Path):
    result = route_task(
        tmp_path,
        "Implement the bounded fix for SUPPORT_TICKET.md.",
        likely_files=["inventory/migration.py", "inventory/service.py"],
        confidence="high",
    )
    assert result["eligible"] is False
    assert result["reason"] == "high_risk_task"


def test_router_directive_requires_parent_review_and_fallback(tmp_path: Path):
    result = route_task(
        tmp_path,
        "Add CSV export support in report.py with tests.",
        likely_files=["report.py", "tests/test_report.py"],
        confidence="high",
    )

    directive = result["directive"]
    assert "exactly one" in directive
    assert "contextguard-worker" in directive
    assert "not a full-history fork" in directive
    assert "review the worker diff" in directive
    assert "continue locally" in directive
