from contextguard.output_compactor import compact_output


def test_repeated_log_error_deduplication():
    output = "\n".join(["ERROR item 1 failed", "ERROR item 2 failed", "ok"])
    compact = compact_output(output, "")
    assert len(compact["errors"]) == 1
    assert compact["line_count"] == 3


def test_one_line_large_output_is_clipped():
    compact = compact_output("x" * 10_000, "")
    assert len(compact["summary_lines"][0]) < 600
    assert "truncated" in compact["summary_lines"][0]


def test_compact_output_records_shown_bytes():
    compact = compact_output("ERROR one\nERROR two\n")
    assert compact["compact_bytes"] > 0
    assert compact["raw_bytes"] > compact["compact_bytes"]


def test_compact_output_separates_unique_failures_warnings_and_tests():
    output = """FAILED tests/test_index.py::test_cache - AssertionError: bad hash
FAILED tests/test_index.py::test_cache - AssertionError: bad hash 2
WARNING deprecated option
Traceback (most recent call last):
  File \"app.py\", line 12, in run
ValueError: broken
2 failed, 4 passed in 1.20s
"""
    compact = compact_output(output)
    assert compact["failed_tests"] == ["tests/test_index.py::test_cache"]
    assert compact["warnings"] == ["WARNING deprecated option"]
    assert len(compact["errors"]) == 2
    assert compact["test_summary"] == "2 failed, 4 passed in 1.20s"
    assert compact["stack_traces"]


def test_compact_output_emits_actionable_evidence_and_escalation_metadata():
    output = """FAILED tests/test_api.py::test_create - AssertionError: expected 201
Traceback (most recent call last):
  File "app/api.py", line 42, in create
AssertionError: expected 201
1 failed, 8 passed in 0.40s
"""

    compact = compact_output(output)

    assert compact["evidence"]["outcome"] == "failed"
    assert compact["evidence"]["locations"] == ["app/api.py:42"]
    assert compact["evidence"]["failed_tests"] == ["tests/test_api.py::test_create"]
    assert compact["confidence"] == "high"
    assert compact["escalation"]["required"] is False
    assert compact["next_action"] == "Inspect the listed location, patch, then rerun only the failed test."
    assert compact["evidence_fingerprint"]


def test_compact_output_requests_local_escalation_for_unexplained_failure():
    compact = compact_output("process stopped unexpectedly\n")

    compact["exit_code"] = 1
    from contextguard.output_compactor import finalize_evidence

    finalized = finalize_evidence(compact)
    assert finalized["confidence"] == "low"
    assert finalized["escalation"]["required"] is True
    assert finalized["escalation"]["reason"] == "failed_without_diagnostic"


def test_unknown_outputs_keep_distinct_evidence_fingerprints():
    first = compact_output("generated value alpha\n")
    second = compact_output("generated value beta\n")

    assert first["evidence_fingerprint"] != second["evidence_fingerprint"]


def test_passing_test_evidence_discourages_redundant_validation():
    compact = compact_output("12 passed in 0.30s\n")

    assert compact["evidence"]["outcome"] == "passed"
    assert compact["next_action"] == "Reuse this passing result until relevant code changes."


def test_zero_failed_test_summary_is_passing():
    compact = compact_output("0 failed, 12 passed in 0.30s\n")

    assert compact["evidence"]["outcome"] == "passed"


def test_git_diff_content_is_not_classified_as_failure():
    output = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-raise RuntimeError('failed')
+return 'fixed error'
"""
    compact = compact_output(output, command="git diff -- app.py")

    assert compact["errors"] == []
    assert compact["evidence"]["outcome"] == "unknown"
    assert compact["signal_lines"][0].startswith("diff --git")
