# changy.md

See [contextguard/changy.md](contextguard/changy.md) for the detailed implementation protocol.

## 2026-06-09

- Built the initial ContextGuard Codex plugin MVP under `contextguard/`.
- Added repository-root marketplace metadata for GitHub source installation.
- Verified tests with `python3 -m pytest`: 19 passed.
- Verified plugin schema with `plugin-creator/scripts/validate_plugin.py`: passed.

## 2026-06-09 Readiness Pass

- Strengthened ContextGuard internals for real use before manual testing.
- Expanded tests to 29 cases.
- Added benchmark harness and richer metrics.

## 2026-06-09 Savings Improvements

- Added medium noisy-output compaction and shorter high-confidence capsules.
- Added visible lifetime savings estimates in status/report.
- Expanded tests to 34 cases.
- Realistic A/B improved to 81.64% estimated token savings with identical patch and passing tests.

## 2026-06-09 Marketplace Presentation

- Updated marketplace-facing plugin metadata and visuals.
- Corrected developer name to Giminger Consulting.
- Added branded PNG icon, logo and screenshot assets.

## 2026-06-09 Marketplace Manifest Alignment

- Aligned `plugin.json` interface metadata with the new ContextGuard marketplace copy.
- Removed screenshot metadata so the plugin page relies on `icon.png` and `logo.png`.
- Changed plugin category metadata to `Productivity`.

## 2026-06-09 Complex Context Savings Test

- Re-validated the plugin manifest and full test suite: 34 passed.
- Ran the built-in benchmark harness across 7 fixtures.
- Ran a complex RAW-vs-ContextGuard feature simulation for temporary billing price override windows.
- Result: both workflows passed the same 6 feature tests with identical invoice output.
- Measured estimate: RAW 219,896 tokens vs ContextGuard 3,138 tokens, saving 216,758 tokens or 98.57%.

## 2026-06-09 Harder Time And Token Test

- Ran a harder RAW-vs-ContextGuard simulation for risk-aware order fulfillment with holds, partial inventory allocation, fraud signals, shipping-zone blocks, surcharges and audit trails.
- Result: both workflows passed the same 31 tests and produced identical sample fulfillment output.
- Measured estimate: RAW 664,211 tokens vs ContextGuard 4,417 tokens, saving 659,794 tokens or 99.34%.
- Local harness time: RAW 0.7779s, ContextGuard 1.5808s, meaning ContextGuard was slower locally because of init/capture overhead.
- Projected model-processing time at 3,000 tokens/s: RAW 222.1815s total vs ContextGuard 3.0532s total, a projected 98.63% time reduction.

## 2026-06-09 Hardest Returns Benchmark

- Ran a harder valid RAW-vs-ContextGuard simulation for resilient returns and refund orchestration.
- Result: both workflows passed the same 53 tests and produced identical sample return output.
- Measured estimate: RAW 1,319,139 tokens vs ContextGuard 4,263 tokens, saving 1,314,876 tokens or 99.68%.
- Local harness time: RAW 0.8120s, ContextGuard 1.5270s, meaning ContextGuard was slower locally because of init/capture overhead.
- Projected model-processing time at 3,000 tokens/s: RAW 440.5250s total vs ContextGuard 2.9480s total, a projected 99.33% time reduction.

## 2026-06-09 Ultimate Dispute Benchmark

- Ran the final valid RAW-vs-ContextGuard simulation for a NovaPay dispute-resolution engine.
- Result: both workflows passed the same 87 tests and produced identical dispute decision output.
- Measured estimate: RAW 2,439,341 tokens vs ContextGuard 4,178 tokens, saving 2,435,163 tokens or 99.83%.
- Projected model-processing time at 3,000 tokens/s: RAW 814.1161s total vs ContextGuard 3.0763s total, a projected 99.62% time reduction.
- Projection from 640M raw monthly tokens at $450: same reduction ratio would be about 1.096M ContextGuard tokens and about $0.77 equivalent usage cost.
# 2026-06-10 Adaptive Maximum Efficiency

## Audit

- Baseline: 34 tests passed in 3.82 seconds.
- Existing components: lifecycle hooks, SQLite index, task classifier/capsule, command rewriting/capture, output compactor, large-file summaries, metrics, and a seven-fixture benchmark.
- Problems: duplicated policy wording, visible initialized-session status, stale `Adaptive Maximum Savings` naming, weak task relevance scoring, byte-only benchmarks, incomplete structured failure summaries, and no first-class final-response quality policy.
- Measured overhead: managed instructions plus a representative capsule used about 250 estimated tokens; the representative capsule recommended unrelated test files.

## Planned Solution

- Centralize output and final-response policy.
- Structure and deduplicate captured failures, warnings, tests, and traces while preserving complete local logs and exit codes.
- Tighten progressive context retrieval and reuse verified session state.
- Measure ContextGuard overhead and require same-result benchmark equivalence.
- Update tests and documentation, then run the complete suite before pushing `main`.

## Implemented

- Added a single `Adaptive Maximum Efficiency` output policy with task complexity and final-response semantic checks.
- Made initialized session startup silent and reduced managed policy text below 700 bytes.
- Added compact verified session capsules, progressive retrieval metadata, automatic escalation reasons, and true unchanged-file read avoidance.
- Added structured unique errors, warnings, failed tests, test summaries and stack traces while preserving complete stdout/stderr, exit codes and durations locally.
- Added managed-policy, capsule, cache, tool-call and net-reduction metrics.
- Rebuilt the benchmark around ten baseline/optimized scenarios with equivalent exit-code and repository-hash acceptance.
- Updated README, architecture templates, benchmark documentation and changelog.

## Validation and Limitations

- Complete suite: 47 tests passed in 4.38 seconds.
- Benchmark: all 10 scenarios produced the same exit code and repository hash.
- Measured exposed-output reductions included 18,104 bytes for verbose tests, 28,228 bytes for large JSON, 12,921 bytes for repeated errors and 4,364 bytes for a 300-file listing.
- Small-output scenarios intentionally showed no byte reduction; the capture subprocess added roughly 60-125 ms in this local benchmark.
- Token reductions remain estimates until a controlled real Codex A/B run exposes server-side usage measurements.

## 2026-06-10 Real Codex Hard A/B

- Built a reproducible real-Codex benchmark using two identical isolated settlement repositories, `gpt-5.5`, medium reasoning, the same prompt, 130 tests, canonical CLI validation, JSONL usage parsing and wall-clock measurement.
- The first run used 129 tests and appeared favorable, but artifact review found that the ContextGuard implementation was not idempotent for a third duplicate event. That result was rejected, the validation suite was strengthened, and both trials were rerun from scratch.
- Final quality result: raw and ContextGuard both passed all 130 tests and produced the same canonical settlement result (`posted_minor=9174`).
- Raw: 255,166 input tokens, 44,478 uncached input tokens, 5,516 output tokens, 1,258 reasoning tokens, 12,304 tool-output bytes, 20 commands and 124.423 seconds.
- ContextGuard: 328,934 input tokens, 28,134 uncached input tokens, 5,023 output tokens, 1,231 reasoning tokens, 92,353 tool-output bytes, 18 commands and 124.711 seconds.
- ContextGuard reduced uncached input by 36.75%, combined generated tokens by 7.68% and commands by 10.0%.
- ContextGuard increased total input by 28.91%, input plus generated tokens by 27.96%, tool-output bytes by 650.59% and final-response bytes by 15.19%. Time increased by 0.23%, effectively unchanged.
- Problem: on Codex CLI 0.128.0, ContextGuard hooks executed but `PreToolUse.updatedInput` and `PostToolUse.replacementOutput` were not applied. The optimized agent's initial failing pytest run exposed 80,573 bytes instead of a compact summary.
- Solution: update hook response envelopes for supported Codex CLI versions, add an integration test proving command replacement and output replacement, then rerun this exact A/B benchmark.
- Result classification: mixed and currently negative on total token/tool-output efficiency; not a ContextGuard win.

## 2026-06-10 Hook Compatibility Fix

- Reproduced the failure on Codex CLI 0.128.0 with a 278,889-byte command result.
- Root cause: ContextGuard emitted hook response fields at the top level, while Codex requires `hookSpecificOutput`; `PostToolUse.replacementOutput` is unsupported; and Python module validation commands such as `python3 -m pytest` bypassed command classification.
- Confirmed that CLI 0.128.0 executes hooks but ignores `PreToolUse.updatedInput`, even with the current documented envelope.
- Confirmed that CLI 0.128.0 supports PostToolUse replacement through `decision=block` and compact `reason` feedback; a live probe showed the model receiving the compact summary and local full-output path rather than the full log.
- Fixed SessionStart, UserPromptSubmit and PreToolUse envelopes; changed PostToolUse to supported replacement feedback; added a PostToolUse fallback for noisy medium output; recognized `python -m pytest|ruff|mypy`; and migrated `hooks.json` to the current nested schema.
- Added raw versus model-visible tool-output metrics to the real A/B harness because Codex JSON events retain raw command output even when hooks replace what the model sees.
- Validation before A/B rerun: 56 tests passed. The exact A/B rerun was deferred only because the Codex account reported its usage limit until 4:13 PM Europe/Berlin.

## 2026-06-10 Hard A/B Rerun And Upstream Blocker

- Hardened the benchmark so a ContextGuard trial is invalid unless it runs the exact baseline command, records hook invocations and compacts at least one output.
- Both CLI 0.128.0 and pinned CLI 0.139.0 reruns passed all 130 tests with identical canonical output, but were rejected because `codex exec` dispatched zero hooks.
- Verified the problem with marker-only hooks and found matching upstream Codex issues 25875, 26383 and 26452.
- Published the exact rejected token/time samples with `accepted_run: false`; no ContextGuard efficiency claim is made from those inactive trials.

## 2026-06-10 Direct Hard Output A/B

- Added a direct RAW-versus-real-ContextGuard PostToolUse benchmark using the identical 130-failure pytest output.
- RAW exposed 80,573 bytes / 20,650 `o200k_base` tokens; ContextGuard exposed 2,132 bytes / 543 tokens.
- ContextGuard saved 20,107 visible tokens, a 97.37% reduction, at 42.5 ms median additional processing time across eleven samples.
- The complete archived output remained byte-identical, and the visible compact output retained the total failure summary, 20 failed-test names and representative root failures.
- Full suite: 61 tests passed.
