# ContextGuard for Codex

[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-blue.svg)](LICENSE)

> **License notice:** Free for personal and noncommercial use. A commercial license is required for company, professional, client, and revenue-related use.

This repository contains the installable Codex plugin at `contextguard/`.

ContextGuard helps Codex produce the same correct result with less wasted input, less unnecessary output and faster task completion through local indexing, compact session reuse, structured command capture and one Adaptive Maximum Efficiency policy.

See [contextguard/README.md](contextguard/README.md) for installation and usage.

Further information and benchmark report: [context-guard-plugin.vercel.app](https://context-guard-plugin.vercel.app)

## OpenAI Build Week 2026

ContextGuard existed before Build Week, but a substantial part of the current 0.9.3 release was designed, implemented, tested, and documented during the event on July 18, 2026.

GPT-5.6 Sol in Codex was used to inspect real token-usage traces, compare cached input, uncached input, output, and API-cost behavior, implement the transparent zero-roundtrip workflow, and run isolated RAW-versus-ContextGuard acceptance tests. Codex accelerated the work by exposing the behavioral differences between experiments, editing the plugin and benchmark harness, and validating each approach against the same hidden test suite.

The key technical decision came from an initially unsuccessful experiment: compacting tool output alone created additional agent turns and increased total cost. The final Build Week implementation therefore optimizes the complete interaction pattern with normal shell commands, bounded task evidence, reuse of verified context, and fewer retrieval roundtrips.

In one controlled paired GPT-5.6 Sol maintenance benchmark, ContextGuard reduced total tokens from 389,814 to 164,797 (57.72%), commands from 13 to 5 (61.54%), and standard API-cost equivalent from $0.629986 to $0.365395 (42.00%). Both arms passed 144/144 hidden tests and produced the same canonical and concurrency result. This is one scoped stochastic sample, not a universal savings or subscription-quota guarantee.

The representative Codex Build Week session ID is `019f767d-b7d1-7f72-85c7-629ff269a833`. Detailed setup, testing, architecture, and benchmark instructions are in [contextguard/README.md](contextguard/README.md).

## License

ContextGuard is source-available software.

It is free to use for personal and genuinely noncommercial purposes under the [PolyForm Noncommercial License 1.0.0](LICENSE).

Commercial, professional, organizational, and internal company use requires a separate commercial license from Giminger Consulting.

Using ContextGuard within a company, for client work, as part of a paid professional activity, or to obtain a commercial advantage is considered commercial use.

For details, see:

- [LICENSE](LICENSE)
- [Commercial Licensing](COMMERCIAL-LICENSE.md)

Commercial licensing contact: **https://www.giminger.com**

## Quick start

Add the `GimingerConsulting/ContextGuard` marketplace, install the plugin, start a project thread, and run `$contextguard-setup`. ContextGuard creates a project-local capture runner; hooks are optional defense in depth.
