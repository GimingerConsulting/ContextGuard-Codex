# Changelog

## 0.9.2

- Added deterministic output-kind routing for tests, diffs, searches, JSON, repetitive logs and generic output without adding a model dependency.
- Expanded automatic capture to Cargo, Go, Docker/Podman, Kubernetes, Terraform, Gradle/Maven, GitHub CLI, Bun, TypeScript/ESLint/Vitest and structured API responses.
- Added exact session-scoped SHA-256 output references so repeated captured output becomes a short reversible receipt while the full output remains archived locally.
- Added schema-only JSON signals and normalized repeated-log collapsing; raw JSON values remain hidden from visible summaries.
- Preserved bounded non-string operational scalars such as `expected_version=0` in structured inspection while continuing to redact secret, credential, token, email, account and similar fields.
- Added a feature-specific RAW-vs-ContextGuard benchmark: 30,367 versus 645 visible tokens (97.88% reduction), including 97.33% improvement on command families that 0.9.1 left as raw passthrough.
- Passed the corrected three-pair real Codex support-ticket A/B with exact output equality and median reductions of 19.59% total input, 35.82% uncached input, 20.15% cached input and 64.36% tool output.

## 0.9.1

- Changed default source inspection from a raw first-200-line read to a deterministic structural outline, following the token-budgeted repository-map pattern used by mature coding agents.
- Added Python AST outlines and bounded cross-language declaration outlines with import prioritization, per-file line budgets and single-line truncation.
- Kept exact `--symbol` and line-range reads unchanged so compact orientation never replaces required source evidence.
- Reduced the measured three-file large-repository inspection from 1,942 to 938 visible tokens (61.07%) while preserving successful command execution; full raw source remains available through exact follow-up inspection.
- Standardized the package and plugin version as plain `0.9.1` without a date-based build suffix.

## 0.9.0 efficiency extension (2026-07-11)

- Added task-conditioned evidence packets with explicit-file ranking, bounded relevant excerpts, hashes and likely-test handles.
- Added safe structured summaries to `contextguard inspect` for JSON, JSONL, CSV, TSV and logs; raw values are omitted and variable error fields are redacted.
- Removed duplicate cross-session/checkpoint injection from every UserPromptSubmit and moved dynamic session state behind a stable cache-friendly prefix.
- Compacted routing directives and made high-risk routing decisions final so agents do not spend commands inspecting worker configuration.
- Added `contextguard orient --query ...` for an explicit task evidence packet.
- Added a deterministic mechanism benchmark showing the packet plus structured evidence at 1,983 visible bytes versus 8,590 bytes in the prior live orientation phase, a 76.92% reduction. A post-change live Codex rerun was quota-rejected at zero tokens and is not treated as evidence.

## 0.4.1

- Strengthened managed project instructions so large `sed`, `tail`, `head`, `cat`, `awk`, `jq`, `rg`, pipeline and multi-file inspections must use the project capture runner.
- Extended command classification and hook rewriting to cover multi-file inspection commands while preserving direct small, bounded single-source reads.
- Added regression coverage for the exact CI-log and large-JSONL bypass patterns observed in real Codex A/B runs.
- Documented that hosts without shell interception still rely on agent compliance with managed project instructions.

## 0.4.0

- Added versioned, allow-listed session checkpoints for compact resume context.
- Added session-scoped SHA-256 tracking for exact repeated `cat` and `sed -n` reads, with immediate invalidation when a file changes.
- Added a non-blocking command budget for repeated repository listings, repository checks, excessive full-suite validation, and long command sequences.
- Added status metrics for tracked commands, repeated reads, and emitted budget advice.
- Kept model selection entirely user-controlled and preserved all commands, validation, exit codes, and archived output.

## 0.3.2

- Made every lifecycle hook fail open when a running thread references a plugin cache directory removed by an update or uninstall.
- Added regression coverage for stale cached hook commands so missing plugin files cannot block prompts, tools, compaction or thread completion.

## 0.3.1

- Fixed wheel and editable installation by restricting setuptools discovery to the `contextguard` package.
- Declared and validated Python 3.9 as the minimum runtime used by Codex plugin hooks and scripts.
- Removed the real Codex A/B harness dependency on `codex exec` lifecycle-hook dispatch; optimized trials now require the host-independent project capture runner.
- Added packaging, Python-minimum and non-interactive runner regression coverage.

## 0.3.0

- Added the executable project-local `.contextguard/bin/contextguard` runner.
- Changed managed project instructions to route noisy commands through `capture` before stdout reaches Codex.
- Made output protection independent of lifecycle hook dispatch and output replacement behavior.
- Added truthful runner readiness reporting, isolated installed-runner acceptance and a real Codex host A/B benchmark.
- Measured the accepted host A/B at 33.33% fewer input tokens, 35.06% fewer uncached input tokens, 95.07% less tool output and 28.42% lower elapsed time for the same validated result.

## Unreleased

- Added the Adaptive Maximum Efficiency output policy and final-response quality checks.
- Added structured unique errors, warnings, failed tests, stack traces and complete local output retention.
- Added compact session-resume capsules, cache-reuse metrics and bounded policy overhead reporting.
- Reworked benchmarks around equivalent exit codes and repository-state hashes across ten scenarios.

## 0.1.0

- Initial MVP with local project initialization, SQLite indexing, managed documentation, command capture, large-output compaction, lifecycle hooks, explicit skills, tests and marketplace metadata.
