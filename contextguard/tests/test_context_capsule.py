from pathlib import Path

from contextguard.context_capsule import build_capsule, build_session_capsule, persist_session_capsule
from contextguard.utils import estimate_tokens


def test_task_capsule_limit(tmp_path: Path):
    for index in range(50):
        (tmp_path / f"payment_{index}.py").write_text("x=1\n")
    capsule = build_capsule(tmp_path, "payment bug", token_limit=80)
    assert estimate_tokens(capsule) <= 80
    assert "ContextGuard capsule" in capsule


def test_high_confidence_capsule_is_short(tmp_path: Path):
    (tmp_path / "billing_service.py").write_text("class BillingService:\n    pass\n")
    capsule = build_capsule(tmp_path, "fix BillingService")
    assert len(capsule.encode()) < 260


def test_high_confidence_capsule_stays_compact_with_many_matches(tmp_path: Path):
    for index in range(25):
        (tmp_path / f"subscription_billing_{index}.py").write_text(
            f"class SubscriptionBilling{index}:\n    pass\n"
        )
    capsule = build_capsule(tmp_path, "fix subscription billing")
    assert len(capsule.encode()) < 300


def test_normal_task_capsule_stays_below_300_estimated_tokens(tmp_path: Path):
    (tmp_path / "billing.py").write_text("class BillingService:\n    pass\n")
    capsule = build_capsule(tmp_path, "fix BillingService")
    assert estimate_tokens(capsule) < 300


def test_session_capsule_keeps_only_verified_resume_facts(tmp_path: Path):
    facts = {
        "current_objective": "finish output policy",
        "changed_files": ["contextguard/output_policy.py"],
        "verified_tests": ["12 tests passed"],
        "known_failures": [],
        "active_constraints": ["preserve correctness"],
        "next_action": "run full suite",
        "ignored_blob": "x" * 20_000,
    }
    persist_session_capsule(tmp_path, facts)
    capsule = build_session_capsule(tmp_path)
    assert "finish output policy" in capsule
    assert "ignored_blob" not in capsule
    assert estimate_tokens(capsule) < 400


def test_session_capsule_renders_versioned_checkpoint_without_metadata_noise(tmp_path: Path):
    persist_session_capsule(
        tmp_path,
        {"current_objective": "resume efficiently", "next_action": "run focused test"},
    )

    capsule = build_session_capsule(tmp_path)

    assert "resume efficiently" in capsule
    assert "checkpoint_id=" not in capsule
    assert "version=" not in capsule


def test_session_capsule_prioritizes_frontier_and_trims_tail(tmp_path: Path):
    persist_session_capsule(
        tmp_path,
        {
            "current_objective": "finish compaction",
            "likely_relevant_files": [
                "contextguard/contextguard/context_capsule.py",
                "contextguard/hooks/pre_compact.py",
            ],
            "likely_relevant_symbols": [
                "build_session_capsule@contextguard/contextguard/context_capsule.py:46",
            ],
            "changed_files": ["contextguard/contextguard/session_state.py"],
            "verified_tests": ["test_session_state.py::test_checkpoint_persistence_merges_sparse_updates"],
            "known_failures": ["none"],
            "active_constraints": ["keep the resume capsule bounded"],
            "next_action": "run focused tests",
            "integration_points": [f"adapter-{index}" for index in range(24)],
            "verified_facts": [f"fact-{index}" for index in range(24)],
            "rejected_hypotheses": [f"hypothesis-{index}" for index in range(24)],
        },
    )

    capsule = build_session_capsule(tmp_path, token_limit=180)

    assert "current_objective=finish compaction" in capsule
    assert "likely_relevant_files=contextguard/contextguard/context_capsule.py, contextguard/hooks/pre_compact.py" in capsule
    assert "likely_relevant_symbols=build_session_capsule@contextguard/contextguard/context_capsule.py:46" in capsule
    assert "changed_files=contextguard/contextguard/session_state.py" in capsule
    assert "verified_tests=test_session_state.py::test_checkpoint_persistence_merges_sparse_updates" in capsule
    assert "known_failures=none" in capsule
    assert "active_constraints=keep the resume capsule bounded" in capsule
    assert "next_action=run focused tests" in capsule
    assert "integration_points=" not in capsule
    assert "verified_facts=" not in capsule
    assert "rejected_hypotheses=" not in capsule
    assert estimate_tokens(capsule) <= 180


def test_session_capsule_is_shorter_than_minimal_raw_re_read_payload(tmp_path: Path):
    persist_session_capsule(
        tmp_path,
        {
            "current_objective": "finish compaction",
            "likely_relevant_files": [
                "contextguard/contextguard/context_capsule.py",
                "contextguard/hooks/pre_compact.py",
            ],
            "likely_relevant_symbols": [
                "build_session_capsule@contextguard/contextguard/context_capsule.py:46",
            ],
            "changed_files": ["contextguard/contextguard/session_state.py"],
            "verified_tests": ["test_session_state.py::test_checkpoint_persistence_merges_sparse_updates"],
            "known_failures": ["none"],
            "active_constraints": ["keep the resume capsule bounded"],
            "next_action": "run focused tests",
        },
    )

    capsule = build_session_capsule(tmp_path, token_limit=160)
    # Representative minimal rehydration without an execution checkpoint: the
    # agent must re-read the implementation seam, hook, and focused test before
    # it can recover the same verified next step.
    raw_payload = "\n".join(
        [
            "def persist_checkpoint(root: Path, facts: dict) -> dict:",
            "    existing = load_checkpoint(root)",
            "    compact = {}",
            "    for key in CHECKPOINT_FIELDS:",
            "        new_value = facts.get(key)",
            "        if _checkpoint_value(new_value):",
            "            compact[key] = new_value",
            "            continue",
            "        existing_value = existing.get(key)",
            "        if _checkpoint_value(existing_value):",
            "            compact[key] = existing_value",
            "def build_session_capsule(root: Path, token_limit: int = 400) -> str:",
            "    parts = []",
            "    for key in SESSION_FIELDS:",
            "        value = facts.get(key)",
            "        if value:",
            "            parts.append(f'{key}={_render_session_value(value)}')",
            "    while estimate_tokens(text) > token_limit and parts:",
            "        parts.pop()",
            "event = read_event()",
            "persist_session_capsule(info.root, event)",
            "session_capsule = build_session_capsule(info.root, token_limit=240)",
            "if session_capsule:",
            "    parts.append(session_capsule)",
            "if manifest.exists():",
            "    archive = archive_index_summary(info.root)",
            "    if archive['entries']:",
            "        parts.append('Reuse archived evidence before re-running noisy commands.')",
            "while parts and estimate_tokens('\\n'.join(parts)) > 320:",
            "    parts.pop()",
            "context = result['hookSpecificOutput']['additionalContext']",
            "assert 'current_objective=finish compaction' in context",
            "assert 'changed_files=contextguard/contextguard/session_state.py' in context",
            "assert 'verified_tests=test_session_state.py::test_checkpoint_persistence_merges_sparse_updates' in context",
            "assert 'active_constraints=keep the resume capsule bounded' in context",
            "assert 'next_action=run focused tests' in context",
            "assert checkpoint['next_action'] == 'run focused tests'",
            "assert checkpoint['verified_tests'] == ['test_session_state.py::test_checkpoint_persistence_merges_sparse_updates']",
        ]
    )
    raw_tokens = estimate_tokens(raw_payload)
    capsule_tokens = estimate_tokens(capsule)

    assert "current_objective=finish compaction" in capsule
    assert "next_action=run focused tests" in capsule
    assert capsule_tokens <= raw_tokens * 0.5, (capsule_tokens, raw_tokens)
