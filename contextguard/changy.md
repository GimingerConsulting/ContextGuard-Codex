# changy.md

## 2026-06-09

### Changes

- Scaffolded `contextguard` as a Codex plugin using the local `plugin-creator` workflow.
- Implemented Python standard-library MVP: project detection, SQLite indexing, managed documentation, command classification, command capture, output compaction, large-file summaries, metrics and CLI.
- Added bundled lifecycle hooks in `hooks/hooks.json`.
- Added explicit Codex skills for init, status, refresh, report and project uninstall.
- Added `agents/openai.yaml` metadata for each skill.
- Added marketplace metadata at `.agents/plugins/marketplace.json`.
- Added repository-root marketplace metadata so `BurliNYC/ContextGuard` can be used as a GitHub marketplace source while the plugin root remains `./contextguard`.
- Added README, contribution, security, changelog, license and benchmark documentation.
- Added tests for project detection, command rewriting, compaction, large files, capsules, documentation safety and hooks.

### Adjustments

- The plugin is under repository path `contextguard/`, matching the requested tree. The repository root is a container for the installable plugin and exposes a root marketplace file that points to `./contextguard`.
- `plugin.json` does not include a top-level `hooks` field because the current local plugin validator rejects unsupported manifest fields. Hooks are present in `hooks/hooks.json` and documented in the README.

### Problems And Solutions

- Problem: the workspace was not initialized as a Git repository.
  Solution: initialize Git before committing and pushing to `BurliNYC/ContextGuard`.

- Problem: PNG assets are required but the MVP does not need custom artwork.
  Solution: include deterministic placeholder PNG assets for validation and later replacement.

- Problem: skill agent YAML initially used flat metadata keys, but current plugin validation requires an `interface` object.
  Solution: updated `agents/openai.yaml` files to the validator-compatible schema.

- Problem: skill agent asset paths must resolve inside the plugin archive from the plugin root.
  Solution: copied placeholder icons into each skill's `assets/` directory and changed skill metadata icons to `assets/icon.png` and `assets/logo.png`, matching validator rules.

## 2026-06-09 Readiness Pass

### Changes

- Added richer SQLite metadata for symbols, imports, package scripts and tests.
- Improved task capsules with indexed symbols, relevant tests and `ripgrep`-backed content path matching with Python fallback.
- Changed hook command rewrites to use the bundled `scripts/contextguard` path, preserving paths with spaces and avoiding reliance on shell `PATH`.
- Made `PostToolUse` store full large tool output under `.contextguard/tmp/` before returning a compact replacement.
- Persisted `.contextguard/repo_map.json` during init and refresh.
- Added measured metrics for compact output bytes and index refresh duration.
- Added targeted large-file filters for match context and selected line ranges.
- Added an executable local benchmark harness.
- Expanded tests from 19 to 29 cases covering CLI flows, repeated init, paths with spaces, non-zero capture preservation, large output hook storage and runtime network-import absence.
- Fixed benchmark harness import handling so fixture subprocesses can run ContextGuard from temporary project directories.
- Fixed output compaction for one-line large files so compact summaries cap individual lines instead of echoing huge JSON/log records.
- Tuned token-saving behavior from A/B testing: small captured outputs now pass through unchanged, and task capsules are shorter.

### Remaining Limitations

- Current local plugin validation rejects top-level `hooks` in `plugin.json`; hook files are included and documented, but actual hook activation must be confirmed in the target Codex surface after plugin installation.
- Token savings remain conservative local estimates, not verified Codex server-side usage numbers.

## 2026-06-09 Savings Improvements

### Changes

- Added medium noisy-output compaction for test failures and repeated error output above 2 KB.
- Kept small command output passthrough for low-overhead correctness.
- Shortened high-confidence task capsules by reducing list counts and wording.
- Added project lifetime savings visibility in `contextguard status` and `contextguard report`.
- Added measured `estimated_saved_bytes`, `estimated_tokens_saved`, and `estimated_reduction_percent` metrics.
- Added tests for medium noisy-output compaction, lifetime savings visibility, compact byte accounting and compact high-confidence capsules.

### Validation

- Full test suite: 34 passed.
- Plugin validation: passed.
- Realistic subscription-preview A/B after improvements: same patch, both workflows passed 17 tests, ContextGuard reduced estimated tokens from 6,779 to 1,244, saving 5,535 estimated tokens or 81.64%.

## 2026-06-09 Marketplace Presentation

### Changes

- Updated plugin marketplace metadata for a professional Codex plugin detail page.
- Corrected developer branding to `Giminger Consulting`.
- Changed category to `Developer Tools`.
- Replaced placeholder imagery with branded PNG icon, logo and screenshot assets.
- Refined skill display metadata and starter prompts for install-page presentation.

## 2026-06-09 Marketplace Manifest Alignment

### Changes

- Updated `.codex-plugin/plugin.json` interface metadata to use the requested ContextGuard display name, short description, long description, developer name, `Productivity` category, gold brand color, icon, logo and two default prompts.
- Removed screenshot references from plugin metadata because Codex marketplace presentation only needs `assets/icon.png` and `assets/logo.png` for this plugin.
- Updated both marketplace catalog files to keep their category aligned with the manifest.
- Removed the local macOS `.DS_Store` asset file from the plugin package.

### Problems And Solutions

- Problem: the official Codex plugin package uses `.codex-plugin/plugin.json`, while `.agents/plugins/marketplace.json` is the repository marketplace catalog that points Codex at the installable plugin folder.
  Solution: keep both files, use `plugin.json` for the plugin's display metadata, and use the marketplace catalog only to expose `./contextguard` from the GitHub repository.

- Problem: the requested interface block did not include `capabilities`, but current local plugin validation requires `interface.capabilities`.
  Solution: keep `Interactive`, `Read` and `Write` capabilities in the manifest while matching the requested user-facing copy and assets.

## 2026-06-09 Complex Context Savings Test

### Validation

- Plugin manifest validation passed for `contextguard/`.
- Full test suite passed: 34 tests.
- Built-in benchmark harness passed across 7 fixtures with matching RAW and ContextGuard exit codes.
- Smoke-tested `contextguard init`, `contextguard status` and `contextguard report` on a temporary project.

### RAW-vs-ContextGuard Scenario

- Simulated a realistic feature task in a temporary Python billing project with source modules, tests, 30 unrelated report helpers, a large audit log, a large JSON fixture and architecture documentation.
- Task: implement temporary pricing override windows for invoices, including inclusive date windows, unknown-SKU validation, invalid-window validation and most-specific overlapping override behavior.
- RAW workflow used broad project context, full file contents and raw test output.
- ContextGuard workflow used project init, a task capsule, targeted search, selected relevant files and captured test output.
- Both workflows used the same implementation strategy, passed the same 6 feature tests and produced identical sample invoice output.
- Estimated context use: RAW 219,896 tokens, ContextGuard 3,138 tokens.
- Estimated savings: 216,758 tokens, 98.57% reduction, 70.08x lower context volume.

### Problems And Solutions

- Problem: the first benchmark harness attempt failed before measuring because the temporary fixture generator missed a `Decimal` import.
  Solution: added the missing import in the temporary test harness and reran.

- Problem: the next attempt did not place the temporary project's `src/` directory on `PYTHONPATH`, so both RAW and ContextGuard failed import resolution.
  Solution: added project-local `src/` to the subprocess environment and reran.

- Problem: the simulated tests initially asserted `line.unit_price`, but invoice lines are serialized as dictionaries.
  Solution: corrected the temporary test fixture to assert `line["unit_price"]`, then reran until both workflows passed.

## 2026-06-09 Harder Time And Token Test

### RAW-vs-ContextGuard Scenario

- Simulated a larger feature task in a temporary Python commerce project with checkout pricing, inventory allocation, risk/fraud modules, 65 unrelated analytics helpers, 25 legacy tests, a 9,000-line fulfillment audit log, a 3,200-record JSON fixture and long system-design documentation.
- Task: implement risk-aware order fulfillment with customer risk profiles, fraud thresholds, blocked shipping zones, partial inventory allocation, high-risk surcharges and compact audit trails.
- RAW workflow used broad project context, full file contents and raw test output.
- ContextGuard workflow used project init, a task capsule, targeted search, selected relevant files and captured test output.
- Both workflows used the same implementation strategy, passed the same 31 tests and produced identical sample output: `ready 12.00 ['fulfillable:mouse:2', 'surcharge:12.00']`.

### Results

- Estimated context use: RAW 664,211 tokens, ContextGuard 4,417 tokens.
- Estimated savings: 659,794 tokens, 99.34% reduction, 150.38x lower context volume.
- Local harness time: RAW 0.7779 seconds, ContextGuard 1.5808 seconds. ContextGuard was slower locally because init, indexing and capture add tool overhead.
- Projected model-processing time at 3,000 tokens per second: RAW 222.1815 seconds total, ContextGuard 3.0532 seconds total.
- Projected model-time savings: 219.1284 seconds, 98.63% faster end-to-end under that token-throughput assumption.

### Problems And Solutions

- Problem: the first run's temporary `sample()` helper expected an obsolete tuple return shape from the benchmark runner.
  Solution: updated the temporary helper to read the current result dictionary shape and reran successfully.

## 2026-06-09 Hardest Returns Benchmark

### RAW-vs-ContextGuard Scenario

- Simulated a larger temporary Python retail project with orders, catalog, money helpers, risk, returns, 95 unrelated reporting helpers, 45 legacy tests, a 15,000-line returns audit log, a 5,500-record JSON fixture and long returns policy documentation.
- Task: implement resilient returns and refund orchestration with order-state validation, line quantity caps, product return windows, final-sale rules, damage exceptions, region rules, captured-payment validation, partial returns, tax refunds, restocking fees, fraud-aware shipping refunds and audit entries.
- RAW workflow used broad project context, full file contents and raw test output.
- ContextGuard workflow used project init, a task capsule, targeted search, selected relevant files and captured test output.
- Both workflows used the same implementation strategy, passed the same 53 tests and produced identical sample output: `approved 36.00 ['shipping-refund:6.00']`.

### Results

- Estimated context use: RAW 1,319,139 tokens, ContextGuard 4,263 tokens.
- Estimated savings: 1,314,876 tokens, 99.68% reduction, 309.44x lower context volume.
- Local harness time: RAW 0.8120 seconds, ContextGuard 1.5270 seconds. ContextGuard was slower locally because init, indexing and capture add tool overhead.
- Projected model-processing time at 1,000 tokens per second: RAW 1,319.9510 seconds total, ContextGuard 5.7900 seconds total, 99.56% faster.
- Projected model-processing time at 3,000 tokens per second: RAW 440.5250 seconds total, ContextGuard 2.9480 seconds total, 99.33% faster.
- Projected model-processing time at 6,000 tokens per second: RAW 220.6685 seconds total, ContextGuard 2.2375 seconds total, 98.99% faster.

### Problems And Solutions

- Problem: the first version of the temporary benchmark had inconsistent expectations for line-level tax and damage-exception returns, so both RAW and ContextGuard failed final tests.
  Solution: treated the run as invalid, corrected the temporary benchmark fixture to use consistent line-tax and damage-exception semantics, and reran until both workflows passed.

## 2026-06-09 Ultimate Dispute Benchmark

### RAW-vs-ContextGuard Scenario

- Simulated a larger temporary Python payments project with ledger, transaction, dispute, risk, jurisdiction, money and fee services, 140 unrelated reporting helpers, 80 legacy tests, a 26,000-line dispute audit log, a 9,000-record JSON fixture and long dispute operations documentation.
- Task: implement cross-module dispute resolution with transaction-state validation, payment capture checks, customer risk, chargeback history, jurisdiction rules, evidence freshness, duplicate dispute cooldowns, recoverable amount caps, provisional credits, fee exposure, escalation levels and audit trails.
- RAW workflow used broad project context, full file contents and raw test output.
- ContextGuard workflow used project init, a task capsule, targeted search, selected relevant files and captured test output.
- Both workflows used the same implementation strategy, passed the same 87 tests and produced identical sample output: `approved 400.00 150.00 10.00 ['cap:400.00', 'auto-credit:150.00', 'fee:10.00']`.

### Results

- Estimated context use: RAW 2,439,341 tokens, ContextGuard 4,178 tokens.
- Estimated savings: 2,435,163 tokens, 99.83% reduction, 583.85x lower context volume.
- Local harness time: RAW 1.0024 seconds, ContextGuard 1.6836 seconds. Local tool time remains less important than model processing time for this benchmark.
- Projected model-processing time at 1,000 tokens per second: RAW 2,440.3434 seconds total, ContextGuard 5.8616 seconds total, 99.76% faster.
- Projected model-processing time at 3,000 tokens per second: RAW 814.1161 seconds total, ContextGuard 3.0763 seconds total, 99.62% faster.
- Projected model-processing time at 6,000 tokens per second: RAW 407.5593 seconds total, ContextGuard 2.3799 seconds total, 99.42% faster.
- Projected model-processing time at 12,000 tokens per second: RAW 204.2809 seconds total, ContextGuard 2.0318 seconds total, 99.01% faster.

### Cost And Usage Projection

- Using the user's observed 640,000,000 raw tokens and $450 equivalent monthly usage as a rough input, this benchmark's ratio would project to about 1,096,165 ContextGuard tokens and about $0.77 equivalent usage cost for the same class of work.
- This is a benchmark projection, not a guaranteed billing result, because real Codex behavior depends on task shape, model routing, hidden context, tool calls and how much context the agent chooses to load.
# 2026-06-10 Adaptive Maximum Efficiency

- Audit baseline: 34 tests passed; representative policy and capsule overhead was about 250 estimated tokens.
- Identified stale duplicated policy text, noisy startup context, weak relevance scoring, incomplete command summaries, and byte-only benchmarks.
- Planned a centralized output policy, structured tool-output summaries, progressive cached context, same-result benchmarks, bounded overhead metrics, and documentation updates.
- Implemented the policy, compact session reuse, typed output summaries, true unchanged-file read avoidance, expanded metrics and ten same-result benchmark scenarios.
- Validation: 47 tests passed; all benchmark scenarios matched exit codes and repository hashes.
- Limitation: small commands retain capture-process latency, and token values remain estimated pending a real Codex A/B run.

## 2026-06-10 Real Codex Hard A/B

- Added `benchmarks/real_codex_ab.py` with a difficult multi-module settlement fixture, 130 tests, exact Codex JSONL token parsing, isolated homes, result equivalence checks and preserved local artifacts.
- Both raw and ContextGuard runs passed 130 tests and produced identical canonical output.
- ContextGuard reduced uncached input 36.75% and generated tokens 7.68%, but increased total input 28.91% and tool output 650.59%; elapsed time was effectively equal.
- Found a CLI 0.128.0 compatibility defect: hook scripts ran, but command and output replacement fields were ignored. Add version-compatible hook envelopes and integration coverage before rerunning the benchmark.

## 2026-06-10 Hook Compatibility Fix

- Reproduced the hook protocol issue against Codex CLI 0.128.0 and verified the supported PostToolUse replacement path with a live 278,889-byte log probe.
- Added current `hookSpecificOutput` envelopes, supported PostToolUse blocking feedback, noisy-medium fallback compaction, Python module validation classification, nested `hooks.json`, and model-visible tool-output accounting.
- Validation: 56 tests passed. The unchanged hard A/B rerun is pending the external Codex usage reset at 4:13 PM Europe/Berlin.

## 2026-06-10 Hard A/B Rerun And Upstream Blocker

- Added exact-baseline-command enforcement, hook invocation counters, compaction counters, raw/model-visible output accounting and pinned Codex command support to the hard A/B harness.
- Expanded shell hook matching and made PreToolUse payload-driven so command-bearing tool aliases remain compatible across Codex versions.
- Rejected a CLI 0.128.0 sample and a pinned CLI 0.139.0 sample even though both sides passed all 130 tests with identical canonical output: both nominal ContextGuard trials recorded zero hook invocations and zero compacted outputs.
- Reproduced the failure independently with project hooks, user hooks, inline TOML hooks, an installed ContextGuard plugin, trusted projects, `--dangerously-bypass-hook-trust`, and marker-only hooks. Neither PreToolUse nor Stop executed under `codex exec`.
- Confirmed matching upstream Codex reports: issues 25875, 26383 and 26452. The published result is marked blocked and contains the rejected measurements for auditability; it does not claim token savings or regression from runs where ContextGuard never activated.
- Validation after the implementation changes: 58 tests passed and the 130-test fixture self-check passed.

## 2026-06-10 Direct Hard Output A/B

- Added `benchmarks/output_ab.py`, which feeds one identical 130-failure pytest output to the RAW path and the real ContextGuard PostToolUse hook.
- Strengthened compact output with up to 20 visible failed-test names in addition to the summary and representative errors.
- Acceptance requires byte-identical archived full output, a visible test summary, concrete failed tests and fewer visible tokens.
- Measured with `o200k_base`: RAW 80,573 bytes / 20,650 tokens; ContextGuard 2,132 bytes / 543 tokens.
- Savings: 20,107 visible tool-output tokens, 97.37% reduction. Median ContextGuard processing overhead across eleven samples: 42.5 ms.
- Information check passed: the complete archived output SHA-256 matched RAW, while the compact response retained `130 failed`, 20 failed-test names and representative conversion, cap, canonical-scenario and duplicate-reporting failures.
- Final validation: 61 tests passed.
