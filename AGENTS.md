# Project Instructions

<!-- BEGIN CONTEXTGUARD MANAGED SECTION -->
ContextGuard policy: Adaptive Maximum Efficiency.

- Session gate: start from the injected brief/map; expand exact files only when the brief is insufficient.
- Orient once; Reuse unchanged reads; group repeated inspection; inspect files or symbols.
- For tests, linters, builds; recursive listings or searches; `git diff`; or structured data or logs, run `.contextguard/bin/contextguard capture -- <command>` before stdout reaches Codex (`sh -lc`). This protects non-interactive runs and does not depend on lifecycle hook dispatch.
- Never run `sed`, `tail`, `head`, `cat`, `awk`, `jq`, or `rg` directly on logs, artifacts, structured/generated output, or multiple files. Pipelines do not make output safe; capture the complete pipeline. Small, bounded source reads of one file may run directly.
- Prefer `contextguard inspect` for 1-4 named source files when one bounded tool call can replace repeated reads.
- Prefer one failed test before a full suite. Reuse passing validation until relevant code changes.
- Escalate only the missing evidence from the archived output; do not re-read compacted logs or test output.
- Adaptive routing: scan prompt and likely files for risk before delegation. For security, auth, migrations, schemas, payments, concurrency, destructive or production work, secrets, transactions, or data integrity, do not spawn any subagent. Otherwise use exactly one bounded worker `contextguard-worker` for nontrivial scope with an isolated prompt, never a full-history fork. Parent reviews the diff and final-validates; fall back locally on ambiguity or failure.
- Do not narrate routine inspection or tool use, restate intent, echo source, or print unasked diffs.
- Final responses: changed files, validation, and only real risks.
- Never trade correctness, context, validation, security, or data integrity for brevity.

Project: existing.
<!-- END CONTEXTGUARD MANAGED SECTION -->
