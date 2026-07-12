# ContextGuard

[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-blue.svg)](../LICENSE)

> **License notice:** Free for personal and noncommercial use. A commercial license is required for company, professional, client, and revenue-related use.

ContextGuard helps Codex produce the same correct result with less wasted input, less unnecessary output and faster task completion.

Developer: Giminger Consulting

Further information, benchmarks and setup guide: [context-guard-plugin.vercel.app](https://context-guard-plugin.vercel.app)

It optimizes repository input context, repeated session context, terminal and test output, large structured data, model-generated explanations, final responses, and repeated code or diff output. It automatically expands context when correctness requires it.

## What It Does

ContextGuard is a local-first Codex plugin with explicit skills, a project-local capture runner, optional lifecycle hooks and deterministic Python tooling. It indexes repository metadata locally, writes compact project guidance, captures large command output before it reaches Codex, summarizes large data files, and injects small task capsules when there is enough evidence to help Codex start with targeted inspection.

It uses one policy: **Adaptive Maximum Efficiency**. The policy starts with metadata, symbol locations and focused ranges, reuses verified unchanged facts, and escalates through complete symbols, dependencies, files and wider repository context whenever evidence is insufficient.

Within one Codex session, ContextGuard fingerprints exact read-only `cat` and `sed -n` commands. If the same command targets byte-identical files again, it emits one compact reuse hint instead of silently changing or blocking the command. File changes invalidate the hint immediately.

ContextGuard also tracks command families and emits deduplicated, non-blocking guidance when repository listings or checks repeat, when more than two full-suite validations run, or when a session crosses a command milestone. Initial and final full validation remain allowed. Model selection always remains under user control.

The output-efficiency engine suppresses routine narration, request restatement, source echo, full diffs and unrelated closing suggestions by default. Completed-task responses retain changed files, validation results and any real blocker, limitation or unverified assumption. Explicit requests for detailed explanations still take precedence.

## Privacy

ContextGuard sends no repository content or telemetry to external services. It supports Python 3.9 and newer and uses standard-library modules plus SQLite. Local state is stored under `.contextguard/` inside the project.

## License

ContextGuard is source-available software.

It is free to use for personal and genuinely noncommercial purposes under the [PolyForm Noncommercial License 1.0.0](../LICENSE).

Commercial, professional, organizational, and internal company use requires a separate commercial license from Giminger Consulting.

Using ContextGuard within a company, for client work, as part of a paid professional activity, or to obtain a commercial advantage is considered commercial use.

For details, see:

- [LICENSE](../LICENSE)
- [Commercial Licensing](../COMMERCIAL-LICENSE.md)

Commercial licensing contact: **https://www.giminger.com**

## Fast Setup From The Codex Marketplace

ContextGuard supports empty projects and existing repositories. It preserves user-authored content and only replaces sections marked as ContextGuard-managed.

1. Add the GitHub marketplace source:


```bash
codex plugin marketplace add GimingerConsulting/ContextGuard
```

   In the Codex app, the equivalent path is:

```text
Plugins -> Add More -> Add Source -> GitHub
```

2. Install `contextguard` from the ContextGuard marketplace and start a new thread in the project you want to use.

3. Run `$contextguard-setup`. It initializes the project and creates `.contextguard/bin/contextguard`, which protects noisy command output without depending on hooks.

4. Optional: when Codex reports that hooks need review, open `/hooks` and trust the local ContextGuard hooks for automatic session initialization and extra protection on supported surfaces.

5. Start a new thread after initial setup so Codex loads the managed `AGENTS.md` capture policy.

## Smoke Test

Run `$contextguard-setup`, then ask Codex to execute a command that produces substantial repeated output. Afterwards run `$contextguard-status` and `$contextguard-report`.

A successful smoke test shows:

- `Project: initialized`
- `Execution protection: ready`
- a project runner under `.contextguard/bin/contextguard`
- at least one intercepted command after tool use
- full large output archived under `.contextguard/tmp/` when compaction was needed

Hook observations are reported separately. Missing hooks do not disable project-runner protection. Trusting hooks remains optional and ContextGuard never edits hook-trust records.

To update the marketplace, refresh the source in Codex. To update the plugin, pull the repository or update the marketplace source, then reinstall or refresh the plugin in Codex. To disable the plugin, disable it in Codex plugin settings. To remove the marketplace, remove the `GimingerConsulting/ContextGuard` source from Codex.

## Project Initialization

Normal initialization is automatic on the first trusted `SessionStart`. The explicit alternatives are:

```bash
contextguard setup
contextguard init
```

or invoke `$contextguard-setup` or `$contextguard-init` in Codex. Prefer setup because it also checks whether hooks have been observed.

Initialization creates `.contextguard/`, the executable `.contextguard/bin/contextguard` runner, a local SQLite index, managed sections in `AGENTS.md`, `docs/ARCHITECTURE.md`, and `docs/CURRENT_STATE.md`, and backups before replacing existing managed sections. It never blindly overwrites user-authored content.

## Daily Commands

```bash
contextguard setup
contextguard status
contextguard refresh
contextguard report
contextguard orient --query "investigate the issue in SUPPORT_TICKET.md"
contextguard capture -- pytest -q
contextguard inspect app.py data/production.log scenario.json
contextguard large-file data.json --contains error --limit 10
contextguard uninstall-project
```

`status` and `report` show measured raw and compact output bytes, managed-policy and capsule overhead, cache reuse, session command counts, repeated-read detections, command-budget advice, and estimated token reduction. Token values are local estimates, not exact Codex server-side usage numbers.

## Architecture

- Skills provide explicit user commands.
- The project-local runner compacts noisy command output before the host receives stdout.
- Task-conditioned evidence packets rank explicit files and relevant excerpts under a hard token budget before broad exploration.
- Structured inspection reports schemas, counts, severities and redacted error signatures without exposing raw values.
- Hooks provide optional automatic initialization and defense in depth.
- The Python package performs project detection, indexing, documentation updates, command classification, session checkpoints, read fingerprinting, command-budget advice, output capture, large-file summaries and local metrics.
- SQLite stores metadata, hashes, symbols, command executions, cache reuse and conservative savings estimates.

## Quality Guard

ContextGuard never blocks legitimate inspection or skips relevant validation to preserve a token estimate. It does not hide failures, warnings, security concerns or data-integrity risks. Complete command output, stderr, exit code and duration are stored under `.contextguard/tmp/`; Codex receives unique errors, warnings, failed tests and paths for targeted follow-up inspection.

Read reuse and command budgets are advisory. They never select a model, deny a command, cross a SessionStart boundary, or trust a fingerprint after the underlying file changes.

## Supported Platforms

macOS is the primary target. Linux is supported where Python 3 and shell semantics are compatible. `ripgrep` is used when available in future retrieval paths; the MVP keeps a Python fallback.

## Hook Compatibility

Codex hook support varies by surface and CLI version. ContextGuard does not depend on hook dispatch, command rewriting or output replacement: managed project instructions execute noisy commands through the local runner before stdout reaches Codex, including non-interactive runs. Hooks use the current nested schema and remain useful for automatic setup and fallback compaction where supported.

Hook commands are enabled by default in Codex but non-managed hooks require one explicit review in `/hooks`. This trust decision cannot and should not be automated by the plugin. ContextGuard automates project setup immediately after Codex dispatches the trusted `SessionStart` hook.

## Benchmarks

Use `benchmarks/run_benchmarks.py` for deterministic local scenarios and `benchmarks/real_codex_ab.py --run` for a controlled implementation A/B. The June 13 ContextGuard 0.4.0 run used identical temporary projects, prompt, model and validation contract. Both sides passed 130 tests with the same canonical output. RAW versus ContextGuard measured 369,946 versus 156,482 input tokens, 40,346 versus 23,234 uncached input tokens, 1,140,951 versus 11,077 tool-output bytes, 115.546 versus 94.679 seconds, and 12.590 versus 7.342 GPT-5.5 Codex credits. This is one controlled stochastic sample, not a universal savings guarantee.

## Uninstall

Run:

```bash
contextguard uninstall-project
contextguard uninstall-project --yes
```

The first command explains project-local files. The second removes `.contextguard` state. Managed Markdown sections and user content are preserved unless you remove them manually.

## Roadmap

- Richer cross-language caller extraction.
- Broader repeated real Codex A/B samples across task types and host versions.
- More hook-surface compatibility tests.

## Disclaimer

Local report token values are estimates. Real A/B result files use exact Codex `turn.completed.usage` values and remain scoped to their controlled samples.
## Install and update

Install the current plugin from GitHub:

```bash
codex plugin marketplace add GimingerConsulting/ContextGuard
```

Update an existing installation by installing the latest plugin version again, then start a new Codex thread so the refreshed skills, hooks and bundled runner are loaded. ContextGuard 0.9.1 is intended for real-world testing and early production use; token and API savings vary by workflow.

## Initialize a project

For a new or empty project, run:

```bash
contextguard init --path .
```

For an existing project, run the same command from the repository root:

```bash
contextguard init --path .
```

Existing projects keep user-authored AGENTS.md content. ContextGuard inserts or refreshes only its managed section, keeps prior instructions outside that section, and writes backups when it needs to preserve earlier content. After initialization, start a fresh Codex thread in the project so the managed project instructions are present from the beginning of the session.

## Useful commands

```bash
contextguard status
contextguard capture -- python3 -m pytest
contextguard inspect path/to/file.py path/to/other.py
contextguard inspect path/to/file.py --symbol target_function
contextguard inspect path/to/file.py --start-line 120 --end-line 180
contextguard orient --query "fix the issue in SUPPORT_TICKET.md"
contextguard large-file data.json --contains error --limit 10
contextguard session-cost
contextguard lifetime-savings
```

`contextguard capture -- <command>` is the host-independent path for noisy tests, logs, builds, diffs and searches. It stores full stdout and stderr locally, gives Codex a compact evidence summary, and preserves enough information for targeted follow-up inspection. `contextguard inspect` defaults to a compact structural outline of source files; use `--symbol` or an explicit line range when exact source is required. `contextguard session-cost` and `contextguard lifetime-savings` report local token and API-cost estimates; these are not verified Codex server-side billing values.

## Known limitations

- Savings are workload-dependent. ContextGuard helps most when commands produce large logs, repeated failures, big file listings, noisy test output or broad searches.
- Small commands can cost slightly more than they save because the capture wrapper and summaries add a small fixed overhead.
- Session pricing and lifetime savings are local estimates based on ContextGuard's ledger and model-price assumptions, not verified Codex server-side billing or usage-limit accounting.
- ContextGuard preserves raw command output locally, but users still need to inspect the archived evidence when a compact summary is not enough.
- Hook dispatch varies by Codex host surface and version. The managed `AGENTS.md` runner instructions are the stable fallback for non-interactive and host-independent use.
- It does not replace tests, code review, security review, migration review or production validation.
