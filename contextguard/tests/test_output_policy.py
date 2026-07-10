from contextguard.output_policy import (
    POLICY_NAME,
    classify_complexity,
    inspect_final_response,
    render_policy,
)


def test_policy_is_single_adaptive_maximum_efficiency_mode():
    assert POLICY_NAME == "Adaptive Maximum Efficiency"
    policy = render_policy("python")
    assert POLICY_NAME in policy
    assert "Do not narrate routine inspection or tool use" in policy
    assert "Orient once" in policy
    assert "Escalate only the missing evidence" in policy
    assert "contextguard-worker" in policy
    assert "exactly one bounded worker" in policy
    assert "Parent reviews the diff" in policy
    assert "Prefer `contextguard inspect` for 1-4 named source files" in policy
    assert "scan prompt and likely files for risk before delegation" in policy
    assert "do not spawn any subagent" in policy
    assert "isolated prompt, never a full-history fork" in policy
    assert "changed files, validation, and only real risks" in policy
    assert len(policy.encode()) < 2000


def test_task_complexity_controls_visible_planning():
    assert classify_complexity("rename one constant", changed_file_count=1) == "trivial"
    assert classify_complexity("add output policy tests", changed_file_count=2) == "small"
    assert classify_complexity("migrate persistent database schema safely", changed_file_count=6) == "architectural"


def test_final_response_quality_retains_required_facts_without_echoes():
    response = "Changed contextguard/output.py. Validation: 42 tests passed. Risk: benchmark timing varies."
    result = inspect_final_response(
        response,
        changed_files=["contextguard/output.py"],
        validation_required=True,
        risk_required=True,
    )
    assert result["valid"] is True
    assert result["violations"] == []


def test_final_response_rejects_missing_validation_and_unrelated_follow_up():
    result = inspect_final_response(
        "Implemented the change. If you want, I can also redesign the UI.",
        changed_files=["contextguard/output.py"],
        validation_required=True,
    )
    assert "missing_changed_file" in result["violations"]
    assert "missing_validation" in result["violations"]
    assert "unrelated_follow_up" in result["violations"]


def test_requested_detail_allows_longer_explanation():
    verbose = "Detailed explanation requested. " + ("reasoning " * 250)
    assert inspect_final_response(verbose, detailed_requested=True)["valid"] is True


def test_output_policy_rejects_restatement_narration_and_large_echoes():
    response = "You asked me to fix it. Now I'll run tests.\n```python\n" + ("x = 1\n" * 90) + "```"
    violations = inspect_final_response(response)["violations"]
    assert "task_restatement" in violations
    assert "routine_narration" in violations
    assert "source_file_echo" in violations
