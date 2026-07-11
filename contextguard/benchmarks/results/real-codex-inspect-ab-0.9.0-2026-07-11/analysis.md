# Real Codex CLI RAW vs ContextGuard A/B — 2026-07-11

The same support-ticket implementation task ran in isolated Git repositories and isolated `CODEX_HOME` directories with the same Codex CLI, model, reasoning effort, sandbox, prompt, and hidden validation.

## Result

- Valid run: yes
- Equivalent result: yes
- Hidden validation: 144 tests passed in both arms
- RAW: 338,147 input tokens, 44,643 uncached input tokens, 43,619 tool-output bytes, 28 commands, 155.272 seconds
- ContextGuard: 299,429 input tokens, 22,565 uncached input tokens, 12,425 tool-output bytes, 17 commands, 159.497 seconds
- Change with ContextGuard: total input -11.45%, uncached input -49.45%, tool-output bytes -71.51%, commands -39.29%, elapsed time +2.72%
- Generated output changed from 6,427 to 6,796 tokens (+5.74%); reasoning output changed from 1,104 to 1,442 tokens (+30.62%).

ContextGuard achieved the intended context reduction without reducing solution quality. The small latency increase and higher generated/reasoning output are real tradeoffs, but they are materially smaller than the input and tool-output savings in this sample.

## Benchmark hardening

The benchmark previously accepted a run without requiring token reduction and compared ContextGuard command count against a historical threshold of 34. It now requires all of the following:

- equivalent validated quality;
- ContextGuard command count below the paired RAW arm;
- at least 5% less uncached input;
- at least 10% less tool-output volume;
- successful bounded inspection and no quota/rate-limit rejection.

This remains one stochastic RAW-first pair. Repeated counterbalanced pairs are required for a population-level performance claim.
