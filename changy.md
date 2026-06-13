# changy.md

See [contextguard/changy.md](contextguard/changy.md) for the detailed implementation protocol.

## 2026-06-13 ContextGuard Usage Optimization Audit

- Ran the hard settlement RAW-vs-ContextGuard benchmark in two isolated temporary Git projects with identical prompt, GPT-5.5 medium reasoning, required initial failing tests, implementation work, and final 130-test validation.
- Acceptance passed: both repositories finished with 130/130 tests passing and the same canonical settlement output.
- RAW versus ContextGuard: 261,837 vs 112,508 total input tokens (-57.03%), 39,373 vs 30,076 uncached input (-23.61%), 222,464 vs 82,432 cached input (-62.95%), 4,069 vs 3,351 output tokens (-17.65%), 92,679 vs 10,291 tool-output bytes (-88.90%), 11 vs 6 commands (-45.45%), and 110.416s vs 75.504s elapsed (-31.62%).
- At the official 2026-06-13 GPT-5.5 Codex rate card, the sample computes to 10.754 RAW credits versus 7.303 ContextGuard credits: 3.451 credits or 32.09% saved. Per 1,000 credits that is roughly 93 versus 137 equivalent runs, subject to stochastic variation.
- Credit composition was RAW 4.922 uncached + 2.781 cached + 3.052 output, versus ContextGuard 3.760 + 1.030 + 2.513. The largest measured gain came from avoiding repeated cached context and unnecessary command rounds, not only compacting one output.
- The ten-scenario local matrix preserved result hashes and output quality in every case. Small-output scenarios saved no bytes and added roughly 55-80ms capture overhead; noisy tests, JSON, logs, and repository listings avoided 4,364-28,228 visible bytes per command.
- Current project instruction/context files total about 492 tokens (`AGENTS.md` 174, architecture 176, current state 142), so trimming them is useful but not the primary measured opportunity.
- Prioritized opportunities: route routine work to GPT-5.4/mini; add explicit milestone checkpoint-and-resume to avoid carrying long thread history; enforce content-hash-aware read reuse and grouped inspections; avoid capture for confidently small commands; keep full validation once while using targeted tests during iteration; disable unused MCP/plugins and keep nested `AGENTS.md` instructions scoped.
- Main risk: more aggressive summaries or skipped validation could improve metrics while reducing correctness. Future acceptance must continue requiring identical outputs, preserved archives, and complete tests.
- Local artifact: `.contextguard/reports/real-codex-hard-ab-2026-06-13/summary.json`.

## 2026-06-13 Isolated Real Codex RAW vs ContextGuard A/B

- Created two temporary identical Git projects and isolated Codex homes, then ran the same prompt once with RAW command execution and once through the ContextGuard project runner using `gpt-5.5` with low reasoning effort.
- Acceptance passed: both runs executed exactly one command and returned exactly `OBSERVED 130 FAILURES`; RAW used the direct command and the protected run used `.contextguard/bin/contextguard capture`.
- Real Codex result: input tokens fell from 23,060 to 22,762 (-1.29%), uncached input from 10,004 to 9,706 (-2.98%), output from 131 to 130 (-0.76%), tool output from 38,490 to 1,899 bytes (-95.07%), and elapsed time from 7.557s to 6.752s (-10.65%).
- Deterministic local output check preserved the exit code and byte-identical archived output while reducing visible output from 38,490 to 2,043 bytes.
- Tokenizer A/B measured 20,650 RAW visible tokens versus 545 protected tokens, saving 20,105 tokens or 97.36% for the noisy command output itself.
- At the official GPT-5.5 standard API rates available on 2026-06-13 ($5/M uncached input, $0.50/M cached input, $30/M output), this single sample is approximately $0.060478 RAW versus $0.058958 protected: $0.00152 or 2.51% lower, about $1.52 per 1,000 equivalent runs.
- Interpretation: ContextGuard has a large direct effect on noisy tool output, but fixed prompt and cached context dominate this one-turn sample. Multi-turn savings may be larger because suppressed output is not carried forward, but this test does not measure that claim.
- Limitation: this is one controlled stochastic Codex sample and API-equivalent pricing, not a Codex subscription billing statement.
- Local artifacts: `.contextguard/reports/host-capture-ab-2026-06-13/` and `.contextguard/reports/output-ab-2026-06-13.json`.

## 2026-06-12 Minimal Low-Usage Regression Test

- Ran only `test_parse_codex_jsonl_extracts_exact_usage_and_tool_output`; result: `1 passed in 0.01s`.
- Used the local ContextGuard runner and intentionally skipped real Codex subprocesses and larger benchmarks to conserve remaining Codex usage.

## 2026-06-12 Small Post-Fix RAW vs ContextGuard Test

- Ran the deterministic 130-failure output benchmark with three timing samples.
- RAW exposed 80,573 bytes / 20,650 tokens; ContextGuard exposed 2,132 bytes / 545 tokens, saving 20,105 tokens or 97.36%.
- Verified byte-identical archived output, retained failure details, and equivalent information.
- Median ContextGuard processing was 56.916 ms, with 48.253 ms overhead beyond raw tokenization.
- Passed the output A/B regression tests (`2 passed`) and the stale-hook plus documentation-safety tests (`8 passed`).
- Assessment: the stale-hook fix works and prevents removed plugin versions from blocking threads. Compression remains effectively equal to the previous 97.37% result, so this is a reliability fix rather than a measurable compression improvement.
- Result artifact: `.contextguard/reports/small-output-ab-2026-06-12.json` (local and ignored).

## 2026-06-12 ContextGuard Setup

- Initialized ContextGuard for the existing project and indexed 131 files.
- Confirmed host-independent execution protection is ready through `.contextguard/bin/contextguard`.
- Confirmed lifecycle hook observation for `SessionStart`, `PreToolUse`, and `PostToolUse`.
- No savings claim was made because this setup run did not execute a measured project-runner workload.

## 2026-06-12 Release 0.3.1 Problem Resolution

- Packaging: configured explicit setuptools package discovery and modern SPDX license metadata. Clean wheel and editable installs are release gates.
- Python runtime: lowered the declared minimum to Python 3.9 after running the complete suite on the system-compatible runtime.
- Non-interactive Codex: removed lifecycle-hook dispatch from the real A/B contract. Optimized `codex exec` trials must prove `.contextguard/bin/contextguard capture` use, so protection works independently of the open upstream hook-dispatch defect.
- Added regression tests for all three issues and updated marketplace-facing documentation.
- Validation: 79 tests passed on Python 3.9 and Python 3.12; editable installation, plugin validation, isolated acceptance and a real runner-backed `codex exec` A/B all passed.

## 2026-06-12 Host-Independent Capture 0.3.0

- Root cause: hook rewriting and replacement are not reliable across Codex hosts, so post-processing cannot guarantee that raw output stays out of model context.
- Added `.contextguard/bin/contextguard`, generated from the installed plugin path during setup and refresh.
- Updated managed project instructions so noisy tests, builds, recursive output, diffs, logs and structured data run through `capture` before stdout reaches Codex.
- Kept hooks as optional defense in depth instead of a readiness requirement.
- Isolated installed-runner acceptance: 2,739 raw tokens versus 665 visible tokens, saving 75.72%, with preserved exit code and byte-identical archived output.
- Accepted real Codex A/B with the same prompt, one command per trial and the same final response: input tokens 34,008 to 22,673 (-33.33%), uncached input 14,808 to 9,617 (-35.06%), tool output 38,490 to 1,899 bytes (-95.07%), elapsed time 9.701 to 6.944 seconds (-28.42%).

## 2026-06-12 Local ContextGuard Compactor Verification

- Confirmed project initialization, a current 124-file index and observed `SessionStart`, `PreToolUse` and `PostToolUse` hooks.
- Confirmed live large-output protection by observing automatic compaction of repository inspection output in this Codex thread.
- Ran the deterministic hard 130-failure output A/B benchmark with eleven timing samples.
- Result: 20,650 raw `o200k_base` tokens versus 545 ContextGuard-visible tokens, saving 20,105 tokens or 97.36%.
- Verified that the archived full output was byte-identical and that the compact output retained the test summary and failed-test information.
- Median hook overhead was 54.376 ms; net overhead beyond raw tokenization was 45.674 ms.
- Limitation: these are local visible-context measurements, not exact Codex account quota or server-side token measurements.

## 2026-06-12 Installed Host Live A/B Investigation

- Ran two byte-identical real `codex exec 0.139.0` smoke trials against the same deterministic noisy command: one raw and one configured with the installed ContextGuard `0.2.0` hooks.
- The raw trial reported 31,558 input tokens; the configured trial reported 32,834 input tokens, but the optimized trial recorded zero hook heartbeats and zero compactions, so this comparison is invalid and is not a ContextGuard result.
- Repeated the optimized trial with project-local `.codex/hooks.json`, enabled hooks and `--dangerously-bypass-hook-trust`; the CLI still dispatched zero hooks. Its 33,176 input tokens are likewise rejected as evidence.
- Ran the same noisy-output smoke test through the active Codex Desktop project where `SessionStart`, `PreToolUse` and `PostToolUse` heartbeats are observed.
- ContextGuard locally recorded 12,053 raw bytes versus 2,507 compact bytes for the intercepted result, a 79.20% local reduction, and archived the intercepted output.
- Problem: the agent transcript still exposed additional raw tool output after the compact ContextGuard summary. Therefore a successful hook heartbeat and local `model_visible_bytes` estimate do not yet prove that the host removed the original output from the model context.
- Conclusion: the plugin currently has strong deterministic compactor tests, but this installed-host test does not prove lower Codex account quota consumption. Do not market server-side or five-hour-limit savings until a host reports exact usage with hooks observed and the original tool result absent.

## 2026-06-12 Hybrid Onboarding

- Added automatic first-thread initialization for empty and existing projects after Codex hook trust.
- Added `$contextguard-setup`, hook heartbeats and honest not-observed/partial/observed diagnostics.
- Changed every bundled skill to use the plugin-local runner instead of requiring a global executable.
- Added complete marketplace install, `/hooks` trust and smoke-test instructions.
- Verified the packaged flow with 69 tests, plugin validation, isolated acceptance and a real Codex 0.139.0 marketplace installation.
- Isolated hard-output result: 14,581 raw visible tokens versus 530 ContextGuard-visible tokens, saving 14,051 or 96.37% with byte-identical archived output.
- Remaining upstream limitation: ContextGuard cannot approve its own non-managed hooks, and Codex surfaces that do not dispatch hooks cannot receive automatic output protection.

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

## 2026-06-10 Isolated Installation Acceptance

- Added a deterministic pre-install acceptance test using an isolated copy of the publishable plugin.
- Confirmed one-time initialization works for an empty project and an existing Git project while preserving user-authored instructions.
- Confirmed SessionStart, UserPromptSubmit, PreToolUse and PostToolUse logic works automatically in the simulated lifecycle.
- Confirmed byte-identical archived full output and preserved failure information.
- Measured 14,581 RAW tokens versus 528 ContextGuard-visible tokens: 14,053 saved, or 96.38%, with 49.9 ms median hook time across fifteen samples.
- Guarantee applies to the packaged ContextGuard logic; Codex host hook dispatch and stochastic model output remain outside the deterministic guarantee.
- Full suite: 62 tests passed.

## 2026-06-12 ContextGuard Live Plugin And Usage Audit

### Version And Activation

- Fetched `origin/main` and confirmed local `HEAD`, `origin/main`, and the installed plugin cache all use commit `696dbea18119fed9e934ad35cc5a8ff8dd1ff86d` (`feat: add host-independent capture runner`).
- Confirmed the installed plugin is version `0.3.0`, is enabled as `contextguard@contextguard`, and all six configured hook definitions have trusted hashes.
- Compared the complete committed plugin tree against `~/.codex/plugins/cache/contextguard/contextguard/0.3.0`; no file differences were found.
- Confirmed live execution in this Codex thread: ContextGuard generated the task capsule, recorded SessionStart/PreToolUse/PostToolUse heartbeats, compacted tool responses, and archived complete outputs under `.contextguard/tmp/`.
- Current live metrics at audit time: 327 hook heartbeats, 49 compacted outputs, 450,606 raw bytes reduced to 50,662 model-visible bytes across those compacted outputs.

### Validation

- Full test suite on Python 3.12: `76 passed in 9.77s`.
- Ten-scenario benchmark: all scenarios preserved exit codes, result hashes, and output-quality checks.
- Isolated publishable-plugin acceptance: passed automatic initialization, SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, runner usage, exit-code preservation, byte-identical archives, and retained failure details.
- Direct hard-output A/B: 20,650 RAW visible tokens versus 543 ContextGuard-visible tokens, saving 20,107 tokens or 97.37%; median added processing time was 43.5 ms in this run.
- Isolated hook acceptance A/B: 14,581 RAW visible tokens versus 530 ContextGuard-visible tokens, saving 14,051 tokens or 96.37%; median hook time was 45.5 ms.
- Host-independent real Codex A/B on `codex-cli 0.139.0` and `gpt-5.5`: both sides executed exactly one command and returned the identical required response. Tool output fell from 38,490 to 1,899 bytes, a 95.07% reduction.

### End-To-End Usage And Time

- The fresh real Codex sample used 22,938 RAW versus 22,631 ContextGuard total input tokens, a 1.34% reduction, and 135 versus 127 output tokens, a 5.93% reduction.
- The same sample took 6.925 seconds RAW versus 8.001 seconds with ContextGuard, a 15.54% increase. Small commands can therefore be slower because capture and summarization add local overhead.
- Prompt-cache distribution changed materially: RAW had 19,200 cached and 3,738 uncached input tokens; ContextGuard had 13,056 cached and 9,575 uncached input tokens. Under the current GPT-5.5 rate card, this single run is approximately 0.81 RAW credits versus 1.46 ContextGuard credits despite lower total input.
- A previously accepted identical benchmark sample recorded 34,008 RAW versus 22,673 ContextGuard input tokens and 9.701 versus 6.944 seconds, approximately 2.19 versus 1.47 credits. The opposite outcomes prove that one stochastic host run is not enough for a universal savings percentage.
- Conclusion: large tool-output reduction is deterministic and substantial; end-to-end Codex usage-limit and latency savings are workload-, cache-, model-, and session-dependent. ContextGuard should not claim a fixed percentage reduction in Codex usage limits without a multi-run randomized benchmark.

### Problems And Solutions

- Problem: a normal modern `uv run` project installation failed before tests because setuptools discovered multiple top-level packages (`hooks`, `skills`, `assets`, and `contextguard`). The plugin copy/install path still passed acceptance and the live installed plugin works.
  Solution: configure explicit setuptools package discovery for the Python package and add a clean wheel/editable-install smoke test before the next release.
- Problem: the machine default `/usr/bin/python3` is Python 3.9.6 while `pyproject.toml` declares Python 3.10 or newer. Current hooks executed successfully, but the runtime contract is inconsistent.
  Solution: either enforce a Python 3.10+ hook interpreter during installation or lower and test the declared minimum if Python 3.9 is intentionally supported.
- Problem: direct lifecycle hooks still do not dispatch under isolated `codex exec` 0.139.0 tests, matching the existing upstream blocker; the host-independent project runner remains the working noninteractive fallback.
  Solution: retain the runner-based path and keep rejecting any benchmark that cannot prove hook or capture-runner activation.

### Audit Artifacts

- Full command and hook captures: `.contextguard/tmp/`.
- Test and benchmark logs: `contextguard/.contextguard/audit-2026-06-12/`.
