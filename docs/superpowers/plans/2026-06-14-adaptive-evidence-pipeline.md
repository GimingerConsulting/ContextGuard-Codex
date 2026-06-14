# Adaptive Evidence Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce redundant model-visible evidence and exploration while preserving RAW-equivalent validated outcomes.

**Architecture:** Extend output compaction with structured evidence and confidence signals, persist output fingerprints in session state, and render concise actionable capture responses with targeted escalation paths. Keep complete output archives as the correctness fallback.

**Tech Stack:** Python 3, pytest, JSON session state, Codex hooks and capture runner.

---

### Task 1: Structured Evidence

**Files:**
- Modify: `contextguard/contextguard/output_compactor.py`
- Test: `contextguard/tests/test_output_compactor.py`

- [ ] Add failing tests for decisive evidence, confidence and escalation reasons.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement structured evidence extraction without removing archived output.
- [ ] Run focused tests until green.

### Task 2: Repeated Output Suppression

**Files:**
- Modify: `contextguard/contextguard/session_state.py`
- Modify: `contextguard/contextguard/output_capture.py`
- Test: `contextguard/tests/test_session_state.py`
- Test: `contextguard/tests/test_cli_flows.py`

- [ ] Add failing tests for repeated equivalent captured output.
- [ ] Verify the tests fail because fingerprints are not persisted.
- [ ] Persist compact evidence fingerprints and render a short prior-evidence reference.
- [ ] Verify focused tests pass.

### Task 3: Actionable Budgets And Escalation

**Files:**
- Modify: `contextguard/contextguard/optimization_advisor.py`
- Modify: `contextguard/contextguard/output_capture.py`
- Modify: `contextguard/contextguard/output_policy.py`
- Test: `contextguard/tests/test_cli_flows.py`
- Test: `contextguard/tests/test_output_policy.py`

- [ ] Add failing tests for phase-aware concrete next actions and local escalation.
- [ ] Verify red state.
- [ ] Implement concise advice and escalation metadata.
- [ ] Verify focused tests pass.

### Task 4: Version, Documentation And Validation

**Files:**
- Modify: plugin version metadata and documentation files discovered in the repository.
- Modify: `changy.md`
- Modify: `contextguard/changy.md`

- [ ] Update the plugin patch version and journals.
- [ ] Run focused tests, full test suite, package validation and deterministic benchmarks.
- [ ] Run a counterbalanced realistic RAW/ContextGuard benchmark.
- [ ] Commit, push `main`, install the new plugin build and verify active status.
