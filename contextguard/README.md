# ContextGuard

ContextGuard helps Codex complete the same work with less wasted context.

It is designed to reduce unnecessary repository exploration, repeated file reads, oversized command output and raw-data ingestion while automatically expanding context when correctness requires it.

## What It Does

ContextGuard is a local-first Codex plugin with explicit skills, lifecycle hooks and deterministic Python tooling. It indexes repository metadata locally, writes compact project guidance, captures large command output to disk, summarizes large data files, and injects small task capsules when there is enough evidence to help Codex start with targeted inspection.

It uses one policy: **Adaptive Maximum Savings**. The policy starts with metadata, search hits and focused ranges, then escalates to larger context whenever correctness requires it.

## Privacy

ContextGuard sends no repository content or telemetry to external services. It uses Python 3 standard library modules and SQLite. Local state is stored under `.contextguard/` inside the project.

## Install From GitHub Marketplace Source

Add the marketplace source:

```bash
codex plugin marketplace add BurliNYC/ContextGuard
```

In the Codex app:

```text
Plugins -> Add More -> Add Source -> GitHub
```

After adding the source, install `contextguard` from the ContextGuard marketplace. Review the bundled hooks before trusting them. They are local Python scripts under `hooks/` and do not use a network API.

To update the marketplace, refresh the source in Codex. To update the plugin, pull the repository or update the marketplace source, then reinstall or refresh the plugin in Codex. To disable the plugin, disable it in Codex plugin settings. To remove the marketplace, remove the `BurliNYC/ContextGuard` source from Codex.

## Project Initialization

Run once in a project:

```bash
contextguard init
```

or invoke `$contextguard-init` in Codex.

Initialization creates `.contextguard/`, a local SQLite index, managed sections in `AGENTS.md`, `docs/ARCHITECTURE.md`, and `docs/CURRENT_STATE.md`, and backups before replacing existing managed sections. It never blindly overwrites user-authored content.

## Daily Commands

```bash
contextguard status
contextguard refresh
contextguard report
contextguard capture -- pytest -q
contextguard large-file data.json --contains error --limit 10
contextguard uninstall-project
```

`status` and `report` show project-local lifetime estimates, including measured raw output bytes, compact output bytes, estimated tokens saved and estimated reduction percentage. These are local estimates, not exact Codex server-side usage numbers.

## Architecture

- Skills provide explicit user commands.
- Hooks provide normal runtime behavior with compact context and output protection.
- The Python package performs project detection, indexing, documentation updates, command classification, output capture, large-file summaries and local metrics.
- SQLite stores metadata, command executions and conservative savings estimates.

## Quality Guard

ContextGuard never blocks legitimate inspection just to preserve a token estimate. It encourages escalation from metadata to symbols, snippets, functions/classes, callers, complete files and wider repository context when evidence is insufficient.

## Supported Platforms

macOS is the primary target. Linux is supported where Python 3 and shell semantics are compatible. `ripgrep` is used when available in future retrieval paths; the MVP keeps a Python fallback.

## Known Hook Limitations

Codex hook support varies by surface. The plugin includes `hooks/hooks.json`, but current local plugin validation rejects a top-level `hooks` field in `plugin.json`; this repository keeps the hook config in the official hook folder and documents that adjustment.

## Benchmarks

Use `benchmarks/run_benchmarks.py` to create local fixture projects and compare raw bytes, compact bytes, overhead, execution time and retained error information. Do not treat these as exact Codex usage numbers.

## Uninstall

Run:

```bash
contextguard uninstall-project
contextguard uninstall-project --yes
```

The first command explains project-local files. The second removes `.contextguard` state. Managed Markdown sections and user content are preserved unless you remove them manually.

## Roadmap

- Richer symbol extraction.
- Better package-script and test detection.
- HTML report export.
- More hook-surface compatibility tests.
- A/B procedures based on real completed tasks per Codex usage window.

## Disclaimer

Token values in reports are conservative estimates. ContextGuard does not claim exact Codex server-side usage reduction.
