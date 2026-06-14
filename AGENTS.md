# Project Instructions

<!-- BEGIN CONTEXTGUARD MANAGED SECTION -->
ContextGuard policy: Adaptive Maximum Efficiency.

- Orient once; Reuse unchanged reads; group repeated inspection; then inspect named files or symbols.
- For tests, linters, builds; recursive listings or searches; `git diff`; or structured data or logs, run `.contextguard/bin/contextguard capture -- <command>` before stdout reaches Codex (`sh -lc`). This protects non-interactive runs and does not depend on lifecycle hook dispatch.
- Never run `sed`, `tail`, `head`, `cat`, `awk`, `jq`, or `rg` directly on logs, artifacts, structured/generated output, or multiple files. Pipelines do not make output safe; capture the complete pipeline. Small, bounded source reads of one file may run directly.
- Prefer one failed test before a full suite. Reuse passing validation until relevant code changes.
- Escalate only the missing evidence from the archived output; do not disable protection task-wide.
- Do not narrate routine inspection or tool use, restate intent, echo source, or print unasked diffs.
- Final responses: changed files, validation, and only real risks.
- Never trade correctness, context, validation, security, or data integrity for brevity.

Project: existing.
<!-- END CONTEXTGUARD MANAGED SECTION -->
