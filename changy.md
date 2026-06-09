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
