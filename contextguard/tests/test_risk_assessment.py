from contextguard.risk_assessment import assess_risk, render_no_delegation_directive


def test_migration_file_locks_routing_even_without_prompt_term():
    assessment = assess_risk(
        "Fix the inventory support ticket.",
        likely_files=["inventory/migration.py", "inventory/service.py"],
    )
    assert assessment["locked"] is True
    assert any("migration" in reason for reason in assessment["reasons"])


def test_bounded_feature_stays_unlocked():
    assessment = assess_risk(
        "Add CSV export support in report.py with tests.",
        likely_files=["report.py", "tests/test_report.py"],
    )
    assert assessment["locked"] is False


def test_no_delegation_directive_is_explicit():
    text = render_no_delegation_directive({"locked": True, "reasons": ["migration"]})
    assert "Do not spawn any subagent" in text
    assert "full-history fork" in text