# changy.md

See [contextguard/changy.md](contextguard/changy.md) for the detailed implementation protocol.

## 2026-07-22 — Exact model/token/cost reporting

- Added Codex JSONL-backed session usage with authoritative model attribution, exact token categories, GPT-5.6 Sol/Terra/Luna short- and long-context API pricing, cache-write accounting, and per-model cost breakdowns.
- Updated the legacy GPT-5.5 proxy label to GPT-5.6 Sol while retaining an explicit distinction between API-equivalent cost and Codex subscription billing.
- Unknown future models still report their exact token usage but mark the aggregate API cost incomplete instead of silently applying a wrong price.

## 2026-07-20 — OpenAI Build Week submission documentation

- Added a concise Build Week section to the public root README so judges can directly identify what was substantially extended during the event, how Codex and GPT-5.6 Sol accelerated the workflow, which failed experiment informed the final architecture, and where the representative Codex session can be found.
- Kept the benchmark claims scoped to one controlled paired run and documented identical 144/144 hidden-test quality, avoiding a universal savings or subscription-quota claim.
- No runtime code or installation behavior changed.

## 2026-07-18 ContextGuard 0.9.3 Installation And Website Release

- Promoted the verified transparent zero-roundtrip implementation to the 0.9.3 plugin candidate and aligned plugin/package versions, release notes, CLI snapshot support, dependency evidence, and installation documentation.
- Marketplace release build `0.9.3+codex.20260718183136` passed 251 tests and isolated installed-copy acceptance before publication.
- Installation acceptance remains fail-closed on correctness; the marketing claim remains the measured one-pair result of 57.72% fewer total tokens, 61.54% fewer commands, and 42.00% lower standard GPT-5.6 Sol API cost with 144/144 hidden tests in both arms.
- The ContextGuardWebsite repository is updated separately with the same bounded claim and an explicit one-pair/non-subscription-guarantee disclaimer.
- Website commit `fd706f0` was initially blocked by Vercel because its local author email was not associated with the authorized GitHub account. The website checkout now uses the verified GitHub noreply identity; non-destructive deploy commit `391e4d4` completed successfully and the production domain was checked for the 0.9.3 build, headline, exact-cost section, and disclaimer.

## 2026-07-18 Transparent Zero-Roundtrip ContextGuard

- Replaced the manual ContextGuard CLI workflow with transparent optimization: the managed policy now tells Codex to use normal shell/source commands while hooks handle eligible large output automatically. It explicitly forbids ContextGuard help, brief, archive, and manual wrapper calls, batches independent inspection, combines final validation, and stops investigation once evidence is sufficient.
- Added a content-addressed, one-time task-evidence injection. Repeated or low-confidence prompts remain silent, avoiding permanent cached-history growth and duplicate orientation packets.
- Successful and repeated capture summaries no longer advertise archive retrieval. Only a failed result without a useful diagnostic exposes one bounded expansion path.
- Added standard GPT-5.6 Sol API-dollar accounting at $5.00/M uncached input, $0.50/M cached input, and $30.00/M output. The release gate requires equal behavioral quality, exact usage, no command increase, and at least 50% median API-dollar savings.
- Real GPT-5.6 Sol screen, medium reasoning, same support ticket: both variants passed all 144 hidden tests and produced the same canonical/concurrency results. RAW used 389,814 total tokens, 13 commands, and $0.629986; transparent ContextGuard used 164,797 total tokens, 5 commands, and $0.365395. That is 57.72% fewer tokens, 61.54% fewer commands, and 42.00% lower standard API cost.
- The 50% dollar gate remains rejected. No three-pair run and no website claim were made. Output tokens fell only 29.10%, and GPT-5.6 Sol output is the dominant $30/M cost. The isolated CLI also did not dispatch the project-local capture hook, so `capture_runner_used` remained false; the measured savings came from the managed zero-roundtrip policy rather than capture compression.

## 2026-07-18 GPT-5.6 Sol RAW/ContextGuard Gate Rejected

- Researched the current OpenAI guidance and changed the primary economics metric to Sol credits: uncached input 125, cached input 12.5, and output 750 credits per million tokens. This prevents cheap cached input and expensive output from being treated as equal.
- Added exact usage-event checks, one- or three-pair screening, fail-closed handling for unavailable models, GPT-5.6 Sol support, bounded tool output, low-verbosity configuration, adaptive greenfield/existing-repo orientation, structured-inspection fallback, and concurrent archive-pruning protection.
- The real GPT-5.6 Sol support-ticket screen preserved quality in both arms (144/144 hidden tests), but ContextGuard regressed from 14.1819 to 20.88485 Sol credits (+47.26%) and from 210,101 to 590,196 total tokens (+180.91%). Commands rose from 8 to 26 despite tool output falling from 28,677 to 17,077 bytes.
- Root cause: repeated capture/retrieval turns and redundant orientation replay dominated the saved tool bytes. The generated policy now uses the exact local binary path, bounded source inspection, successful summaries as terminal evidence, at most one archive retrieval, and one failing test followed by one full suite.
- The 50% release gate failed, so no three-pair rerun and no website savings claim were made. The next live run remains blocked on cheap local evidence that the command/turn count can match or beat RAW.

## 2026-07-18 Execution Frontier Resume Capsule

- Fixed sparse PreCompact checkpoint writes so newer partial events no longer erase previously verified objective, file, test, and constraint state.
- Expanded the checkpoint allowlist with execution-frontier fields and made the PreCompact hook emit a bounded resume capsule with objective, relevant files/symbols, changed files, verified tests/failures/constraints, and next action.
- Added regression coverage for checkpoint merges, capsule truncation/prioritization, PreCompact `additionalContext`, and a cheap offline raw-vs-capsule comparison.
- Validation: 44 focused checkpoint, capsule, hook, cross-session, and session-gate tests passed; the deterministic compaction-boundary fixture enforces at least 50% fewer estimated rehydration tokens than RAW rereads.

## 2026-07-13 — 0.9.3 context-firewall rebuild, release gate rejected

- Implemented complete streamed raw-output archives, reversible `cg://output/<sha>` retrieval, bounded line/regex disclosure, non-blocking evidence budgets, semantic-safe source rewriting, cache-stable prompt behavior, and an explicit ≥50% real-Codex release gate.
- Deterministic payload benchmarks passed at 98.59% and 97.51% visible-token reduction with exact raw roundtrips; the complete repository suite, hidden fixture acceptance, compilation, and package build passed.
- The three-pair real Codex gate preserved exact quality but regressed total tokens 10.88% at the median. A follow-up exact-source screen used fewer commands and 65.63% less tool output but still regressed total tokens 2.39% because cached-prefix replay outweighed the savings.
- No push, installation, or release was performed. The durable policy was reduced to its mechanical core; another expensive live A/B is deferred until local evidence indicates a plausible path to the 50% gate.

## 2026-07-12 — 0.9.3 optimization attempt rejected

- Dependency packets, snapshot/delta reads, native compaction, orient-first routing, and a mechanical exploration cap were tested.
- The best single screen saved 48.99%, but its three-pair repeat regressed 35.01% at the median; the cap regressed 38.81%.
- No release, push, or installation was performed. Version 0.9.2 remains the trusted installed version.

## 2026-06-14 Capture Runner Enforcement 0.4.1

- Strengthened generated `AGENTS.md` instructions for the exact large-file bypasses observed in real A/B runs.
- Added automatic classification and hook rewriting for multi-file inspection commands while retaining direct small source reads.
- Added regression coverage for logs, JSONL, pipelines and multi-file inspection.
- Host limitation remains explicit: without `PreToolUse` dispatch or shell interception, enforcement relies on Codex following project instructions.
- Validation: 113 tests passed, plugin schema passed, the 0.4.1 wheel built, and isolated installed-copy acceptance preserved raw output while reducing visible runner tokens 75.39%.
- Updated Codex to `contextguard@contextguard` `0.4.1+codex.20260614093000` and regenerated the project runner from the new cache.

## 2026-06-13 Context Efficiency 0.4.0

- Implemented versioned checkpoint/resume state, session-scoped hash-aware repeated-read detection, and a non-blocking command budget.
- Model selection remains entirely user-controlled.
- Repeated reads are advised only for exact `cat`/`sed -n` commands with unchanged SHA-256 values in the current session; SessionStart and file changes invalidate reuse.
- Command-budget hints cover repeated listings/checks, a third full-suite validation, and long command sequences without denying commands or weakening final validation.
- Added status counters and focused regression coverage.
- Validation: 97 tests passed, plugin validation passed, the 0.4.0 wheel built, and all ten deterministic scenarios preserved equivalent results.
- Final real Codex A/B: both sides passed 130 tests with identical canonical output; ContextGuard reduced input tokens 57.70%, uncached input 42.41%, tool output 99.03%, elapsed time 18.06%, and estimated GPT-5.5 Codex credits 41.69%.
- Upgraded the local marketplace installation to `0.4.0+codex.20260613081000`, regenerated the project runner from that cache, refreshed the project index, and updated the managed `AGENTS.md` policy.

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

## 2026-06-13 Post-Update Validated RAW vs ContextGuard A/B

- Ran a fresh end-to-end comparison on `codex-cli 0.139.0` with `gpt-5.5` and medium reasoning in two isolated Git repositories and two separate `CODEX_HOME` sandboxes.
- Both agents received the same settlement-reconciliation prompt, passed all 130 tests, produced the same canonical JSON result, and completed without timeout. The ContextGuard trial was accepted only after proving use of `.contextguard/bin/contextguard capture`.
- RAW used 243,179 total input tokens, including 55,531 uncached tokens, plus 4,461 output tokens and 1,294 reasoning tokens. It exposed 93,727 tool-output bytes, ran 14 commands, and took 99.765 seconds.
- ContextGuard used 160,418 total input tokens, including 16,930 uncached tokens, plus 3,715 output tokens and 939 reasoning tokens. It exposed 11,057 tool-output bytes, ran 8 commands, and took 81.290 seconds.
- Measured changes: total input -34.03%, uncached input -69.51%, output -16.72%, reasoning output -27.43%, tool-output bytes -88.20%, commands -42.86%, and elapsed time -18.52%.
- Added a deterministic control using the identical 130-failure pytest output. RAW exposed 20,650 `o200k_base` tokens versus 543 ContextGuard-visible tokens, saving 20,107 tokens or 97.37%, while preserving a byte-identical archive and the relevant failure information.
- Conclusion: this update produced a clear end-to-end usage reduction in the fresh controlled sample, and noisy-output reduction remains deterministic. Codex subscription usage limits are not directly exposed, so the measured token reduction is strong evidence of lower usage pressure, not proof of a fixed quota multiplier for every workload.
- Artifacts: `contextguard/benchmarks/results/real-codex-hard-ab-2026-06-13/` and `contextguard/benchmarks/results/output-ab-2026-06-13.json`.

## 2026-06-13 Realistic Production Backend A/B

- Added a reusable heavier real-Codex benchmark for a legacy inventory backend upgrade: schema migration, backward-compatible API responses, idempotency, optimistic version conflicts, atomic concurrent reservations, deterministic JSON audit logs, CLI behavior, large historical logs and 329 tests.
- Ran RAW and ContextGuard on `codex-cli 0.139.0`, `gpt-5.5`, medium reasoning, identical prompts, separate Git repositories and separate `CODEX_HOME` sandboxes.
- Both implementations passed all 329 tests and produced identical canonical reservation, migration and concurrency results. The ContextGuard run proved `.contextguard/bin/contextguard capture` use.
- RAW: 251,429 input tokens, 65,061 uncached input tokens, 5,217 output tokens, 1,184 reasoning tokens, 291,844 tool-output bytes, 16 commands and 147.982 seconds.
- ContextGuard: 222,214 input tokens, 35,590 uncached input tokens, 4,850 output tokens, 1,791 reasoning tokens, 16,930 tool-output bytes, 8 commands and 111.667 seconds.
- Changes: total input -11.62%, uncached input -45.30%, output -7.03%, tool-output bytes -94.20%, commands -50.00%, elapsed time -24.54%. Reasoning tokens increased 51.27%; output plus reasoning increased from 6,401 to 6,641 tokens (+3.75%). Input plus generated tokens still fell from 257,830 to 228,855 (-11.24%).
- Conclusion: ContextGuard reduced overall usage pressure and completion time on this realistic multi-module task, with the strongest effect on uncached input and noisy tool output. A single stochastic run cannot establish a universal percentage or direct Codex subscription quota multiplier.
- Artifact: `contextguard/benchmarks/results/real-codex-backend-ab-2026-06-13/summary.json`.

## 2026-06-13 Human Support-Ticket Three-Pair A/B

- Added a human-maintenance benchmark where agents receive only support ticket INC-4821, production-style logs, a legacy inventory service, three public tests and a changelog request. The independent acceptance suite contains 144 ticket-observable hidden cases for migration data preservation, retry idempotency and concurrent oversell prevention.
- Ran three counterbalanced pairs in order RAW/ContextGuard, ContextGuard/RAW, RAW/ContextGuard. Every one of the six Codex runs used its own temporary root and isolated `CODEX_HOME`; no agent could inspect the comparison repository.
- Rejected the first attempted series because repositories shared a parent directory and one RAW agent found the ContextGuard sibling. Also removed hidden assertions about undocumented response metadata and audit implementation details. Neither rejected data nor those non-ticket requirements contribute to the final result.
- Final quality: RAW passed 3/3 implementations and ContextGuard passed 3/3 implementations. Every accepted implementation passed all 144 hidden ticket cases, preserved the legacy API response, passed the concurrency probe and updated the changelog.
- Median RAW versus ContextGuard: input tokens 252,120 vs 331,689 (+31.56%); uncached input 39,143 vs 29,667 (-24.21%); tool-output bytes 44,702 vs 17,971 (-59.80%); output tokens 6,031 vs 7,156 (+18.65%); reasoning tokens 1,455 vs 2,005 (+37.80%); commands 25 vs 16 (-36.00%); elapsed time 152.239s vs 164.315s (+7.93%).
- Per-run variance was large. ContextGuard total input changed by +31.56%, +89.34% and -55.00% across the three pairs, while uncached input changed by +0.76%, -9.93% and -63.41%. One ContextGuard agent directly printed the large warehouse JSONL file during an inspection command outside the capture runner, causing a tool-output outlier despite correct runner use for tests and logs.
- Conclusion: ContextGuard preserved solution quality and reduced median uncached input, commands and visible tool output, but this realistic free-form workflow does not prove lower total input, generated tokens or latency on every run. ContextGuard cannot honestly guarantee a fixed Codex usage-limit multiplier; agent exploration and prompt-cache behavior remain major variables.
- Accepted artifact: `contextguard/benchmarks/results/real-codex-support-isolated-ab-2026-06-13/summary.json`.

## 2026-06-14 Human CI-Investigation A/B

- Added a realistic locally-green/CI-red workflow. Agents received a PR review note, three passing public tests, a 1.9 MB CI failure log, an unfamiliar reporting package and a changelog request. The independent acceptance suite checked 160 timezone, DST, explicit-offset and stable-ordering cases.
- Ran two counterbalanced RAW/ContextGuard pairs in four separate temporary roots and isolated `CODEX_HOME` directories. All four implementations passed all 160 hidden cases, preserved the public API, produced the same canonical CLI output and updated the changelog.
- Median RAW versus ContextGuard: total input 317,463 vs 201,378.5 (-36.57%); uncached input 44,439 vs 36,770.5 (-17.26%); tool output 59,470 vs 28,495.5 bytes (-52.08%); output tokens 4,805.5 vs 4,596 (-4.36%); reasoning tokens 1,469.5 vs 1,420.5 (-3.33%); commands 17.5 vs 16.5 (-5.71%); elapsed time 106.180s vs 104.362s (-1.71%).
- Pair 1, where the ContextGuard agent routed the CI log, tests and diffs through `capture`, reduced total input 43.21%, uncached input 45.94%, tool output 86.62%, generated output 12.55%, reasoning 16.70% and time 6.01%.
- Pair 2 exposed the behavioral limit: the ContextGuard agent directly read the large CI log with ordinary `sed` and `tail`. Total input still fell 28.03%, but uncached input rose 55.83%, tool output rose 11.11%, generated output rose 3.05% and time rose 2.38%.
- Conclusion: ContextGuard's strongest and most repeatable benefit occurs when noisy inspections are actually routed through the project runner. Initialization alone does not prevent an agent from bypassing capture with an unprotected command. Total input can still fall because prompt-cache composition and exploration differ, but that is not a deterministic guarantee.
- Artifact: `contextguard/benchmarks/results/real-codex-ci-ab-2026-06-14/summary.json`.

## 2026-06-14 ContextGuard 0.4.1 Post-Restart Audit

- Verified the active Codex plugin as ContextGuard `0.4.1+codex.20260614093000`; project status reported initialization, execution protection and observed lifecycle hooks.
- Re-ran the deterministic cross-workload matrix. All ten RAW/ContextGuard outcomes remained equivalent. Large noisy outputs produced estimated net context reductions of 4,514 tokens for a verbose test suite, 7,057 for large JSON, 3,230 for repeated log errors and 1,091 for a large repository inspection. Six small or already-bounded workloads produced no token reduction and added about 51-79 ms of local processing overhead.
- Re-ran the realistic locally-green/CI-red task as two counterbalanced pairs in four isolated roots. All four implementations passed the 160 hidden timezone/DST cases, canonical output and changelog checks. Both ContextGuard agents used the capture runner for the large CI log and test output.
- Median RAW versus ContextGuard in the 0.4.1 rerun: tool-output bytes 44,482 vs 11,945 (-73.15%); uncached input 42,185.5 vs 41,679 (-1.20%); commands 21.5 vs 20 (-6.98%). Total input increased from 259,209.5 to 276,047 (+6.50%), generated output increased 30.00%, reasoning increased 19.87% and elapsed time increased 125.52% because the two ContextGuard agents explored substantially longer, especially in pair 2.
- Conclusion: 0.4.1 reliably enforced capture in this scenario and sharply reduced model-visible noisy tool output without reducing solution quality. It does not guarantee lower total tokens, latency or subscription usage on every task; model exploration and prompt-cache composition can outweigh saved tool output. The universal all-project/all-task reduction claim is rejected.
- Usage-limit interpretation: API-key billing should benefit when fewer billable tokens are sent because Codex API usage is token-priced. For ChatGPT/Codex subscription limits, OpenAI publishes plan limits but no conversion from local token counters to the usage window, so no verified quota multiplier or guaranteed number of extra tasks can be claimed.
- Artifacts: `contextguard/benchmarks/results/post-0.4.1-matrix-2026-06-14.json` and `contextguard/benchmarks/results/real-codex-ci-ab-0.4.1-2026-06-14/summary.json`.

## 2026-06-14 ContextGuard 0.4.2 Adaptive Evidence Pipeline

- Added structured evidence extraction for outcomes, failed tests, unique diagnostics and source locations. Confidence and local escalation metadata preserve the full archive fallback when a failed command has no actionable diagnostic.
- Added session-scoped evidence fingerprints. Repeated equivalent large outputs now retain a minimal decisive test/error reference instead of retransmitting the full compact summary.
- Reduced visible overhead by removing command echoes, redundant byte fields, absolute archive paths and obvious next-action narration. Archive references are project-relative while stored metadata keeps complete paths.
- Added a search budget after three searches, stronger evidence-first project guidance and reusable passing-validation semantics without imposing hard command limits.
- Made the realistic CI benchmark model-configurable so quota behavior can be checked separately from product correctness.
- Quality validation: 123 full-suite tests passed; the wheel/sdist build succeeded at version 0.4.2; isolated installation acceptance passed every package, runner, hook, archive and information-retention gate; the CI fixture self-check passed all 160 hidden cases with the canonical output.
- Hard 130-failure output benchmark: 20,650 RAW tokens versus 91 ContextGuard-visible tokens, saving 20,559 tokens or 99.56%, with a byte-identical full archive and retained test summary/failed-test evidence.
- Deterministic matrix preserved equal results and output quality in all ten workloads. Compared with 0.4.1, visible output improved from 1,221 to 946 bytes for verbose tests, 962 to 691 for large JSON, 468 to 199 for repeated log errors and 326 to 156 for large-repository inspection.
- The four-agent GPT-5.5 rerun and the GPT-5.4-mini fallback were both rejected as measurements because the account returned the Codex usage-limit error before any tokens or commands ran. The CLI reported retry availability at 4:15 PM; zero-token artifacts are not treated as benchmark results.
- Artifacts: `contextguard/benchmarks/results/output-ab-0.4.2-2026-06-14.json` and `contextguard/benchmarks/results/post-0.4.2-matrix-2026-06-14.json`.
- Isolated installed-copy measurements: runner output saved 2,191 of 2,739 visible tokens (79.99%); repeated hook output saved 14,487 of 14,581 tokens (99.36%) while retaining byte-identical archives and concrete failure evidence.
- Published commit `ce37730` to GitHub `main`, upgraded the Codex marketplace, installed and enabled `0.4.2+codex.20260614121614`, refreshed the current project runner to the new cache path and regenerated the managed `AGENTS.md` policy.

## 2026-06-14 ContextGuard 0.4.2 Human Support-Ticket Validation

- Ran six independent GPT-5.5 agents as three counterbalanced RAW/ContextGuard pairs in isolated repositories and `CODEX_HOME` directories. The task was a realistic support incident involving legacy inventory migration, retry idempotency, concurrent oversell, production logs, regression tests and a changelog update.
- Quality passed in all six runs. Every implementation passed all 144 hidden migration/retry/concurrency cases, preserved the required core API result, produced the same concurrency result and updated the changelog. Every ContextGuard agent used the project capture runner.
- Paired median ContextGuard change: total input -19.48%, uncached input -15.27%, tool-output bytes -64.47%, output tokens -2.42%, reasoning tokens -19.23%, elapsed time -5.34%. Combined generated tokens changed -6.46%, +45.23% and -11.96% by pair.
- ContextGuard did not reduce every individual run. Pair 2 explored substantially longer: total input +79.25%, generated plus reasoning +45.23% and time +52.47%, despite uncached input -15.27% and tool output -62.44%.
- Command count remains the main weakness. Paired changes were +73.33%, +166.67% and -19.44% (median +73.33%). Command-category inspection showed ContextGuard agents performed more follow-up inspections after compacted evidence, especially in pairs 1 and 2.
- Separate-group medians report uncached input +35.44% because the raw and ContextGuard distributions cross between pairs; the counterbalanced paired median is -15.27% and is the more appropriate comparison for this experiment. Neither metric maps directly to the undisclosed Codex subscription quota formula.
- Conclusion: ContextGuard 0.4.2 works for quality-preserving context reduction on this human workflow and materially lowers noisy tool output. It improves the typical paired token result, but it does not guarantee savings per run and currently trades some output compression for extra inspection calls.
- Artifact: `contextguard/benchmarks/results/real-codex-support-ab-0.4.2-2026-06-14/summary.json`.
# 2026-06-14 - ContextGuard 0.5.0 adaptive model routing

- Pushed commit `cb38407` to GitHub `main`, upgraded the configured ContextGuard marketplace, activated plugin `0.5.0+codex.20260614162403`, refreshed this project, regenerated its project runner, and installed the project-local worker agent.
- Release validation passed 133 tests, `compileall`, `git diff --check`, wheel/sdist build, and isolated installed-copy acceptance. The capture runner preserved raw output and exit status while reducing visible acceptance output by 79.99%.
- Added automatic task routing for bounded, high-confidence implementation work. GPT-5.5 retains orientation, planning, risk decisions, diff review, and final validation; one project-local `contextguard-worker` pinned to GPT-5.4-mini performs the bounded implementation package and focused tests.
- Added conservative exclusions for trivial, ambiguous, security, authentication, migration, schema, payment, concurrency, destructive, production, secret, transaction, and data-integrity work. The parent continues locally whenever delegation is unavailable, incomplete, or ambiguous.
- Added project installation of `.codex/agents/contextguard-worker.toml`, SubagentStart/SubagentStop hooks, routing telemetry, and deterministic UserPromptSubmit routing directives. The directive explicitly requires an isolated spawn because Codex does not permit a changed model on a full-history fork.
- Added a real-Codex model-routing A/B harness and API price-bound calculation. The completed validation pair preserved all 160 hidden cases and canonical output; the routed run started a separate worker thread. Raw GPT-5.5 usage was 380,710 input / 6,017 output tokens; routed aggregate usage was 387,693 input / 5,124 output tokens. Conservative GPT-5.5-only API cost ceilings were $0.559964 raw and $0.500697 routed. Exact mixed-model cost and Codex subscription quota savings remain unavailable because the CLI exposes only aggregate usage.
- A final post-fix live rerun was attempted but both arms were rejected before execution by the account Usage Limit reset at 22:31. Unit coverage validates the corrected no-full-history instruction; the earlier live routed run did include one initial rejected full-history attempt before successfully starting the isolated worker.
# 2026-06-15 - ContextGuard 0.5.1 bounded source inspector

- Pushed feature commit `5327a4f` to GitHub `main`, upgraded the configured ContextGuard marketplace, activated `0.5.1+codex.20260615082846`, refreshed this project, and verified the installed project runner executes bounded multi-file symbol inspection.
- Release validation passed 147 tests, all 10 deterministic equivalence scenarios, source compilation, whitespace checks, wheel/sdist build, and isolated installed-copy acceptance. Deterministic visible output fell from 66,634 to 2,077 bytes (96.88%) with identical exit codes and repository results; install acceptance retained a 79.99% reduction.
- Added `contextguard inspect` for one protected tool call over two to four explicitly named source files. It enforces project-root containment, duplicate/path traversal checks, unsafe artifact and structured-file rejection, binary rejection, byte and selected-line limits, optional symbol or line windows, and stable full-file fingerprints.
- Updated managed guidance to prefer the inspector over repeated reads. Hardened adaptive routing so risk scanning occurs before delegation, high-risk tasks explicitly forbid subagents, and permitted workers must start with isolated prompts rather than full-history forks.
- Live high-risk support benchmark preserved all 144 hidden tests and reduced ContextGuard command events from the previous 34-command baseline to 15 using five inspector calls. Tool output was 23,362 bytes versus 44,256 RAW, with 36,214 versus 63,033 uncached input tokens. That run also exposed an unsafe worker spawn, which the release policy now forbids.
- A clean post-policy rerun was attempted, but both RAW and ContextGuard were rejected before their first token by the Codex Usage Limit, with reset reported for June 19, 2026 at 18:17. The no-worker correction is covered deterministically; a new live proof cannot be claimed until quota returns.

# 2026-07-10 - Resource-bounded capture and faithful evidence compaction

- Audited the repository, the project runner and the installed Codex plugin against real use in this task. The audit found four correctness risks: evidence guidance emitted an invalid one-file `inspect` command, selected windows still loaded full files, generic regexes treated removed `git diff` lines as failures, and family-wide command budgets could block new evidence.
- Changed `contextguard inspect` from two-to-four files to one-to-four files. Single-file evidence escalation now executes directly, while grouped inspection remains available for multi-file work.
- Reworked source inspection and evidence expansion to scan files incrementally and retain only the selected line or symbol window. Explicit windows can safely inspect large source files without loading the entire file into memory; full-file fingerprints and source line/byte counts remain available.
- Replaced hard blocks for repeated repository listings and third full validations with non-blocking advice. Exact unchanged file reads remain blocked because their prior content is safely reusable. Removed the unsafe rule that blocked every later log or structured-data command merely because any earlier evidence existed.
- Added command-aware evidence signals for searches, `git status`, and `git diff`. Diff additions/removals are excluded from generic failure detection, and summaries such as `0 failed, 12 passed` are now correctly classified as passing.
- Replaced `subprocess.run(..., capture_output=True)` with concurrent streaming drains. Each stream keeps a configurable bounded head/tail archive, commands have a configurable timeout, and old archive groups are pruned by command-count and disk-byte budgets. This prevents runaway logs/builds from exhausting process memory or growing `.contextguard/tmp` without limit while preserving diagnostics at both ends.
- Added rolling caps for commands, reads, evidence, routing events and ledger events so session state cannot grow forever.
- Research basis: JetBrains Research found environment observations account for about 84% of an average SWE-agent turn and that simple observation masking more than halved cost while staying competitive with LLM summaries; the hybrid saved a further 7-11% (`https://github.com/JetBrains-Research/the-complexity-trap`). Aider's token-budgeted repository map supports bounded structural context (`https://github.com/Aider-AI/aider`). Chop's open-source command-family filters, log-pattern grouping, bounded signal output and per-command tracking informed the command-aware capture direction (`https://github.com/AgusRdz/chop`). LLMLingua was reviewed but not added because its local model/runtime dependency would make this Codex plugin heavier and less predictable than deterministic observation compaction (`https://github.com/microsoft/LLMLingua`).
- Added regression coverage for one-file inspection, large-file range selection, executable evidence expansion, zero-failure summaries, diff false positives, bounded capture head/tail retention, timeouts, archive pruning, advisory budgets and session-history caps.
- Updated Python package license metadata to the PEP 639 string/license-file form after the release build exposed setuptools' deprecated TOML-table warning; warning detection now also recognizes warning class names such as `SetuptoolsDeprecationWarning`.
- Attempted the requested live same-task Codex CLI RAW/ContextGuard A/B benchmark in isolated projects and `CODEX_HOME` directories. Both arms were rejected before their first command or token by the account usage limit, with reset reported for 2026-07-11 01:54 local time. The zero-token run is stored at `contextguard/benchmarks/results/real-codex-inspect-ab-0.9.0-2026-07-10/` and is explicitly invalid, not presented as a savings result.
- Hardened the benchmark so quota/rate-limit runs are labeled with `valid_run: false` and per-arm `rejection_reasons`; acceptance and quality equivalence cannot pass when Codex did not actually execute.
- Ran the deterministic hard-output A/B as a quota-independent fallback: 20,650 RAW visible tokens versus 91 ContextGuard-visible tokens, 20,559 saved (99.56%), identical archived-output SHA-256, retained failure/summary evidence, and about 71 ms median net wrapper overhead across five samples. Artifact: `contextguard/benchmarks/results/output-ab-0.9.0-2026-07-10.json`.
- Release validation passed 195 tests, source compilation, `git diff --check`, plugin manifest validation, and clean wheel/sdist builds with the license file included and no setuptools deprecation warning.
- Published the release to GitHub `main` as commit `7db450f` after rebasing the two newer upstream README/LICENSE commits. Updated the local `giminger` remote to the repository's new canonical URL, `https://github.com/GimingerConsulting/ContextGuard-Codex.git`.
- Upgraded the configured `contextguard` marketplace, installed and enabled `contextguard@contextguard` version `0.9.0+codex.20260710191640`, and refreshed this project through the installed cache copy. Installed-runner verification passed one-file bounded inspection and reports execution protection ready, lifecycle hooks observed, 90.87% lifetime context reduction, and 1,233,747 estimated lifetime net tokens saved. These savings are estimates, not Codex subscription quota telemetry.
- `codex plugin enable` was attempted but this CLI has no such subcommand; no fix was needed because `codex plugin add contextguard@contextguard` installed the new version in the enabled state, confirmed by `codex plugin list`.

# 2026-07-11 - Live Codex CLI RAW vs ContextGuard token A/B

- Reran the same isolated support-ticket task through the Codex CLI after credits reset. Both RAW and ContextGuard used the same model, reasoning effort, prompt, sandbox, hidden validation, fresh Git repository and separate `CODEX_HOME`; neither arm was quota/rate limited.
- Quality was equivalent: both Codex runs exited successfully and passed all 144 hidden migration, retry and concurrency checks with matching canonical and concurrency outputs.
- RAW used 338,147 total input tokens, including 44,643 uncached; emitted 43,619 tool-output bytes; ran 28 commands; and completed in 155.272 seconds.
- ContextGuard used 299,429 total input tokens, including 22,565 uncached; emitted 12,425 tool-output bytes; ran 17 commands with four bounded `inspect` calls; and completed in 159.497 seconds.
- Paired change: total input -11.45%, uncached input -49.45%, tool-output bytes -71.51%, commands -39.29%, elapsed time +2.72%. Output tokens rose 5.74% and reasoning-output tokens rose 30.62%, so the run demonstrates strong context reduction with a small latency and generation tradeoff rather than universal improvement in every metric.
- Audit found the harness could previously accept without token savings and compared commands against a historical 34-command baseline. Hardened acceptance to require paired RAW command improvement, at least 5% uncached-input reduction and at least 10% tool-output reduction while retaining the existing quality, inspect-use, no-worker and quota-validity gates.
- Added unit coverage for material paired savings and for rejecting an uncached-input regression even when command count improves. The saved live run satisfies the stronger gates: 49.45% uncached-input, 71.51% tool-output and 39.29% command reduction.
- Artifact: `contextguard/benchmarks/results/real-codex-inspect-ab-0.9.0-2026-07-11/summary.json`; concise interpretation: `analysis.md`. Limitation: this is one stochastic RAW-first pair; counterbalanced repeated pairs are required for population-level claims.
- Release validation passed 197 tests, plugin manifest validation and `git diff --check`. Cachebuster updated to `0.9.0+codex.20260711083224` for the bundled benchmark hardening.
- Marketplace upgrade exposed a stale-runner failure: the project runner embedded the installed plugin cache path, and upgrading removed that cache before reinstall/refresh, causing `ModuleNotFoundError: No module named 'contextguard.cli'`. Completed the reinstall directly through `codex plugin add`, then refreshed the project from the new cache.
- Fixed the update path by installing a project-local runtime copy under `.contextguard/runtime/contextguard` and generating the runner against that stable copy. Runtime replacement is atomic, excludes Python cache files and removes stale modules on refresh. `project_runner_ready` now verifies both the executable and local runtime entrypoint.
- Added regression tests proving the project runner executes from the local runtime and refresh replaces stale runtime files. Targeted runner/CLI validation passed 17 tests.
- Final validation after the runner fix passed 199 tests, source compilation, plugin manifest validation and `git diff --check`. Release cachebuster: `0.9.0+codex.20260711083627`.
- Published benchmark hardening as `d2a02c4` and the cache-independent runner fix as `75618a5` to GitHub `main`. Upgraded the configured marketplace, installed and enabled `0.9.0+codex.20260711083627`, then refreshed the project through that installed copy.
- Post-install verification confirmed the runner now imports from the stable project-local `.contextguard/runtime` path rather than `~/.codex/plugins/cache`, status reports execution protection ready with lifecycle hooks observed, and six installed-copy runner/benchmark tests passed.

# 2026-07-11 - Task-conditioned evidence and cache-aligned context reduction

- Analyzed the accepted live Codex pair in detail. ContextGuard's 17 commands emitted 12,425 tool-output bytes; the first eight orientation commands emitted 8,590 bytes (69.1%). The largest remaining observations were source inspection (2,902 bytes), ticket/docs inspection (1,877), worker-policy search (1,553), and a fallback log/data search (1,482).
- Research basis: Aider ranks tree-sitter repository identifiers under a token budget (`https://aider.chat/docs/repomap.html`); JetBrains Research found simple observation masking can cut coding-agent cost by roughly half without a significant solve-rate loss (`https://github.com/JetBrains-Research/the-complexity-trap`); OpenAI documents exact-prefix caching and static-first/dynamic-last prompt layout (`https://openai.com/index/unrolling-the-codex-agent-loop/`); SWE-agent's ACI work supports succinct, LM-oriented commands and bounded views (`https://arxiv.org/abs/2405.15793`).
- Added a task-conditioned evidence packet with explicit file references weighted above generic content matches, bounded matching excerpts, likely-test handles, SHA expansion references, a 420-token hard limit, and an untrusted-evidence label. Added `contextguard orient --query ...` and automatic packet injection on high-confidence prompts.
- Extended `contextguard inspect` to safely summarize 1-4 JSON, JSONL, CSV, TSV or log files. Summaries expose types, keys, counts, nulls, severities and redacted error signatures without raw field values. JSONL and log summarization now stream instead of loading whole files.
- Removed repeated cross-session and checkpoint capsules from every UserPromptSubmit because SessionStart already injects them. Task capsules now enforce their token limit by progressively dropping detail instead of relying on an unreachable newline-list truncation branch.
- Reordered the session gate so stable policy and execution guidance precede repo and dynamic checkpoint state, disabled the global Codex-surface inventory by default, and added a stable-prefix regression test.
- Compacted worker-routing directives. High-risk routing locks now explicitly say the decision is final and needs no worker-configuration inspection, targeting the unnecessary 1,553-byte search observed in the live run.
- Deterministic mechanism benchmark: task evidence was 702 bytes (~176 estimated tokens), four structured summaries were 1,281 bytes, and the combined 1,983-byte payload was 76.92% smaller than the prior live orientation phase's 8,590 bytes. This proves the mechanism/output boundary, not that a stochastic Codex run will skip every prior command.
- A post-change live RAW/ContextGuard pair was attempted, but both arms were quota-rejected before token 1. The artifact is invalid and no additional live savings claim is made from it.
- Targeted validation passed 75 tests across evidence packets, structured inspection, hooks, routing, capsules, session gate, CLI and the deterministic benchmark.
- Final release validation passed 207 tests, source compilation, plugin manifest validation and `git diff --check`. After removing generic query terms from evidence matching, the final mechanism result improved to 1,983 bytes (76.92% below the prior orientation phase) and the release cachebuster became `0.9.0+codex.20260711085944`.
- Published the evidence/context release as `ebfacda` and the final relevance refinement as `aa11d85` on GitHub `main`. Upgraded the marketplace, installed and enabled `0.9.0+codex.20260711085944`, refreshed the project through the installed copy, verified a relevant `orient` packet, and passed 43 installed-copy evidence/inspection/hook tests.

## 2026-07-12 — Hybrid retrieval and leaner task evidence

- Problem: generated benchmark artifacts could outrank runtime source in the session-start task brief, spending tokens on stale evidence before work began.
- Research: adopted Aider-style repository-map principles (bounded, dependency-aware orientation), reciprocal-rank fusion for combining weak retrieval signals, observation masking findings from JetBrains' Complexity Trap, and OpenAI's stable-prefix/dynamic-suffix prompt-caching guidance.
- Implementation: added `repo_ranker.py` with weighted reciprocal-rank fusion over explicit paths, path terms, content terms, and symbol evidence; excluded generated build/result/cache trees from default retrieval; exposed ranking reasons for auditability.
- Implementation: updated task classification and evidence gating for normalized hybrid scores, preserved explicit-file priority, reduced dynamic task evidence from 420 to 260 tokens and from six candidate files to four.
- Validation: focused retrieval/classifier/evidence/hooks tests passed 36/36; full suite passed 210/210.
- Real Codex CLI A/B: valid isolated pair, same quality and 144 hidden tests passed per arm. RAW used 196,558 input tokens (37,070 uncached), 38,112 tool-output bytes, 22 commands, 113.787s. ContextGuard used 294,435 input tokens (35,875 uncached), 22,244 tool-output bytes, 16 commands, 124.886s. This saved 3.22% uncached input, 41.64% tool output, and 27.27% commands, but increased total input and elapsed time in this stochastic pair; it therefore failed the preset 5% uncached-input acceptance threshold and is recorded honestly as a valid near-miss, not a pass.
- Follow-up solution: tightened the dynamic evidence packet after the A/B. A second paid run was not used to cherry-pick a favorable sample; the deterministic tests and the failed-threshold live artifact remain the release evidence.
- Sources: https://aider.chat/docs/repomap.html, https://github.com/paul-gauthier/aider/blob/main/aider/repomap.py, https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf, https://github.com/JetBrains-Research/the-complexity-trap, https://openai.com/index/unrolling-the-codex-agent-loop/
- Release: pushed main to the authoritative GimingerConsulting repository (canonical GitHub location: `GimingerConsulting/ContextGuard-Codex`) and installed/enabled plugin build `0.9.0+codex.20260712123616`. The checkout's stale BurliNYC `origin` was corrected to GimingerConsulting to prevent future misdirected pushes.

## 2026-07-12 — Silent post-tool archival and cumulative-context fix

- Root cause: `PostToolUse` ran after Codex had already ingested the original tool response, then injected a second compacted representation through `additionalContext`. The duplicate stayed in every later cached prefix and could erase the savings from bounded commands.
- Fix: post-tool processing now archives complete output, fingerprints repeated evidence, and records metrics silently with zero additional model-visible bytes. Actual reduction is enforced before execution through `PreToolUse` command rewriting and the capture runner.
- Measurement fix: install/output acceptance benchmarks now distinguish archived summaries from model-visible hook context instead of counting a post-hook summary as if it replaced the original response.
- Validation: focused hook/output tests passed 37/37; complete suite passed 210/210.
- Real Codex CLI A/B: valid isolated pair with the same task, 144/144 hidden tests and 152 total tests passed in both arms. RAW: 352,480 input tokens (294,912 cached, 57,568 uncached), 6,403 output tokens, 39,274 tool-output bytes, 27 commands, 172.13s. ContextGuard: 202,573 input tokens (180,736 cached, 21,837 uncached), 5,232 output tokens, 15,728 tool-output bytes, 15 commands, 118.01s.
- Result: 42.53% lower total input, 62.07% lower uncached input, 59.95% lower tool output, 44.44% fewer commands, and 31.44% lower elapsed time at identical hidden-test quality. The preset acceptance gate passed.
- Research basis: observation masking and hybrid masking/summarization results from JetBrains Research; cache-stable ingestion and lifecycle-aware eviction from TokenPilot; immutable raw history plus compact recall handles from SAM/LCM-style memory. Sources: https://arxiv.org/abs/2508.21433, https://github.com/JetBrains-Research/the-complexity-trap, https://arxiv.org/abs/2606.17016, https://arxiv.org/abs/2605.24468, https://github.com/Martian-Engineering/volt

## 2026-07-12 — Website benchmark handoff

- Audited `https://context-guard-plugin.vercel.app` against the newest accepted real Codex CLI result.
- Found that the public hero still uses older 33.8% / 98.3% figures and that multiple benchmark cards currently render zero values; animated headings also remained scrambled in the rendered page during inspection.
- Added `docs/WEBSITE_BENCHMARK_2026-07-12.md` with copy-ready headline, metric cards, comparison table, methodology, plain-language explanation, capacity equivalents, limitations, and evidence pointers.
- Kept measured reductions separate from extrapolation: 1.74x total-input capacity and 2.64x uncached-input capacity are same-workload equivalents, not guaranteed Codex subscription multipliers.

## 2026-07-12 — Balanced ingestion, silent hooks, and counterbalanced A/B

- Research: combined TokenPilot's ingestion-aware stable-prefix strategy, Complexity Trap observation masking, OpenCode DCP duplicate suppression, Aider bounded repository mapping, SWE-agent typed ACI observations, and OpenAI exact-prefix caching guidance.
- Cached-input fix: reduced the session gate from 739 to 171 estimated tokens (76.9%) while continuing to persist the complete repository context map for exact retrieval.
- Uncached-input fix: allowed `PreToolUse` rewrites no longer inject advisory prose; irrelevant user prompts emit no ContextGuard payload; prompt-conditioned task evidence uses a balanced 320-token ceiling after a 180-token experiment caused extra inspections.
- Output fix: successful validation output now uses a typed one-line `ContextGuard PASS` codec. A deterministic 4,710-byte passing transcript produced 121 visible bytes while the exact output remained archived.
- Measurement fix: added counterbalanced RAW-first and ContextGuard-first execution order to the real Codex harness. Acceptance now also requires positive cached-input and model-output reductions.
- Rejected experiment: the 180-token evidence variant remained same-quality and reduced total/cached/tool/output measures, but needed 19 commands and 8 inspections and saved only 1.37% uncached input, below the 5% gate. It was not selected.
- Validation: focused suites passed 61/61 and 36/36; full suite passed 212/212 before the final benchmark-harness assertions, which then passed 4/4.
- Real A/B pair 1 (RAW first): accepted, same quality, 144 hidden tests per arm; total input -7.08%, cached input -4.61%, uncached input -26.28%, model output -20.89%, tool output -55.02%, commands -44.83%, elapsed -16.29%.
- Real A/B pair 2 (ContextGuard first): accepted, same hidden quality, 144 hidden tests per arm; total input -20.55%, cached input -17.50%, uncached input -44.25%, model output -11.35%, tool output -31.98%, commands -37.93%, elapsed -18.64%.
- Counterbalanced median: total input -13.82%, cached input -11.05%, uncached input -35.27%, model output -16.12%, tool output -43.50%, commands -41.38%, elapsed -17.46%. Reasoning tokens increased 26.59% and are reported separately.
- Sources: https://arxiv.org/abs/2606.17016, https://arxiv.org/abs/2508.21433, https://github.com/Opencode-DCP/opencode-dynamic-context-pruning, https://aider.chat/docs/repomap.html, https://swe-agent.com/0.7/background/aci/, https://openai.com/index/api-prompt-caching/
- Release: pushed commit `61ee61f` to `GimingerConsulting/ContextGuard-Codex` main and installed/enabled immutable plugin build `0.9.0+codex.20260712183734`; installed-copy checks confirmed the lean gate, silent allow hook, and typed PASS codec.

## 2026-07-12 — ContextGuard 0.9.2 output-routing research and release gate

- Audited every repository/resource in the supplied source list. Implemented deterministic ideas from sqz, Headroom, context-compression and token-optimizer-mcp; kept LLMLingua, proxy interception, replacement MCP proliferation and unverifiable social-media claims out of the release.
- Added broader command-family capture, content-kind routing, schema-only JSON signals, normalized repetitive-log collapse and exact session-scoped output references backed by local archives.
- The first live A/B exposed a structured-summary information-loss issue (`expected_version=0` was omitted), so that run was rejected. Added bounded safe operational scalar facts without exposing string values or sensitive keys, then reran the unchanged strict benchmark.
- Feature A/B: 30,367 RAW versus 645 visible tokens (97.88% reduction); newly routed 0.9.1 passthrough families improved 97.33%. Existing hard-output compression remained unchanged at 98.59%.
- Corrected live three-pair Codex A/B passed every exact quality gate. Median reductions: total input 19.59%, uncached input 35.82%, cached input 20.15%, tool output 64.36%, model output 11.62%, reasoning output 7.83%, commands 19.35%, elapsed 2.79%.
- Final release validation passed 226 tests, source compilation, whitespace checks, plugin manifest validation, and 0.9.2 wheel/sdist builds.
- Published `82d8641` to authoritative GitHub `main`, upgraded the configured marketplace, installed/enabled plain `contextguard@contextguard` 0.9.2, refreshed the project from that installed copy, and verified the stable local runtime matches the released compactor/inspector with the new routing smoke passing.
- Installed verification then caught a quoted `sh -lc 'git status ...'` edge case that could collapse numbered paths as repetitive logs; fixed command-boundary recognition and added a regression before the final 0.9.2 refresh.

## 2026-07-12 — Dependency-aware working set and snapshot/delta experiment

- Root cause from accepted 0.9.2 traces: optimized arms still emitted a median 13,325 bytes across 16 commands before the first edit because task evidence named the ticket/tests but omitted imported implementation bodies and attached data/log facts.
- Implemented dependency-following task packets with bounded exact symbol excerpts and a strict reuse contract, plus SHA-256/CAS source snapshots that return 70-byte unchanged references or deterministic deltas after edits.
- Deterministic gate: 2,232-byte working set versus 13,325 bytes of measured 0.9.2 pre-edit observations (-83.25%); unchanged reread reduction 88.85%; changed reread 518 bytes.
- Release remains blocked until the unchanged hidden-quality benchmark proves a three-pair total-input result above both the current 19.59% median and the older 42.53% single-pair headline.
- First real screen was rejected despite exact quality: total input improved only 23.22% while tool output improved 70.50%. Trace showed `orient` followed by redundant rereads of the same working set, leaving 21 commands.
- Converted reuse from advice to host-independent enforcement: orient receipts persist hashes; unchanged whole-file inspect/snapshot and repository relisting are denied, bounded symbol/range follow-up remains allowed, and worker shell discovery is forbidden.
