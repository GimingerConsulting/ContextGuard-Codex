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
