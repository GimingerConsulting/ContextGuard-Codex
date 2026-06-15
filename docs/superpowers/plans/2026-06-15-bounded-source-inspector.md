# Bounded Source Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and implement this plan task-by-task.

**Goal:** Add one protected ContextGuard command that reads two to four explicitly named source files in a single tool call without exposing unbounded or generated content.

**Architecture:** A focused `source_inspector` module validates paths against the project root, rejects unsafe file categories, selects bounded line or symbol windows, and emits a compact structured response with content fingerprints. The CLI exposes it as `contextguard inspect`; managed project guidance teaches Codex when to prefer it over repeated single-file reads.

**Tech Stack:** Python standard library, argparse, pytest, existing ContextGuard CLI and policy generation.

---

### Task 1: Inspector behavior

**Files:**
- Create: `contextguard/contextguard/source_inspector.py`
- Create: `contextguard/tests/test_source_inspector.py`

- [ ] Write failing tests for bounded multi-file reads, symbol focus, traversal rejection, unsafe artifact rejection, file-count limits, byte limits, and stable fingerprints.
- [ ] Run only `tests/test_source_inspector.py` and verify the expected failures.
- [ ] Implement the minimal validator and inspector.
- [ ] Rerun the focused tests until green.

### Task 2: CLI and durable guidance

**Files:**
- Modify: `contextguard/contextguard/cli.py`
- Modify: `contextguard/contextguard/output_policy.py`
- Modify: `contextguard/tests/test_cli.py`
- Modify: `contextguard/tests/test_output_policy.py`

- [ ] Add failing tests for `contextguard inspect FILE...`, JSON output, and managed guidance preferring one bounded inspect call for two to four named source files.
- [ ] Verify failures, implement the CLI wiring and policy line, then rerun focused tests.

### Task 3: Parent validation and benchmark

**Files:**
- Modify: `changy.md`
- Modify: `contextguard/changy.md`
- Add benchmark result artifacts under `contextguard/benchmarks/results/`

- [ ] Parent reviews the worker diff and checks unsafe-input handling.
- [ ] Run focused tests, full suite, build, install acceptance, and `git diff --check`.
- [ ] Run the realistic high-risk support RAW/ContextGuard benchmark and the routed CI benchmark.
- [ ] Require equal hidden-test quality, protected output preservation, and fewer ContextGuard command events than the previous 34-command high-risk baseline.
- [ ] Version, commit, push `main`, upgrade the ContextGuard marketplace, refresh the project, and verify the installed version.
