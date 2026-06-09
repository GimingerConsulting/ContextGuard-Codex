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
