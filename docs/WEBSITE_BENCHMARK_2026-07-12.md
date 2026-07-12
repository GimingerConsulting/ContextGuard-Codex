# ContextGuard benchmark — website copy

## Recommended headline

### 42.5% fewer total input tokens. Same result.

In a real Codex CLI maintenance task, ContextGuard reduced total input from **352,480 to 202,573 tokens** while both runs passed **144/144 hidden tests** and **152/152 tests overall**.

For an equivalent workload, that is **1.74x the run capacity from the same total-input budget**. The uncached portion fell by **62.1%**, equivalent to **2.64x the capacity when uncached input is the limiting factor**.

## Metric cards

- **42.5% less total input** — 352,480 RAW vs 202,573 with ContextGuard
- **62.1% less uncached input** — 57,568 RAW vs 21,837 with ContextGuard
- **60.0% less tool output** — 39,274 bytes RAW vs 15,728 bytes with ContextGuard
- **44.4% fewer shell commands** — 27 RAW vs 15 with ContextGuard
- **31.4% faster completion** — 172.13s RAW vs 118.01s with ContextGuard
- **Same verified quality** — 144/144 hidden tests and 152/152 total tests passed in both runs

## Comparison table

| Measured result | Codex without ContextGuard | Codex with ContextGuard | Change |
| --- | ---: | ---: | ---: |
| Total input tokens | 352,480 | 202,573 | -42.53% |
| Cached input tokens | 294,912 | 180,736 | -38.72% |
| Uncached input tokens | 57,568 | 21,837 | -62.07% |
| Output tokens | 6,403 | 5,232 | -18.29% |
| Tool-output bytes | 39,274 | 15,728 | -59.95% |
| Shell commands | 27 | 15 | -44.44% |
| Completion time | 172.13s | 118.01s | -31.44% |
| Hidden tests passed | 144/144 | 144/144 | Same |
| All tests passed | 152/152 | 152/152 | Same |

## What the benchmark tested

The benchmark used two isolated Codex CLI environments with the same repository fixture, task, model, reasoning level, permissions, and hidden acceptance suite.

Codex was asked to investigate a realistic production incident in an unfamiliar Python inventory service. The bug combined duplicate checkout retries, concurrent reservations that could oversell stock, and migration of legacy warehouse records. Each run had to:

1. reproduce the reported problem;
2. identify and fix the root cause;
3. preserve the existing public API;
4. add focused regression tests;
5. pass the public and hidden acceptance suites; and
6. update the changelog.

The RAW arm used normal Codex CLI behavior. The ContextGuard arm used bounded command capture, source inspection, retrieval, evidence archiving, and repeated-read avoidance. Both arms ran with **GPT-5.5**, medium reasoning effort, no approval prompts, and isolated temporary repositories and Codex homes.

## What ContextGuard changed

ContextGuard does not make the model smaller and does not remove required tests or evidence. It changes how repository evidence reaches Codex:

- noisy tests, logs, searches, and generated output are reduced before entering the conversation;
- complete raw output is archived locally for exact retrieval;
- source inspection returns the relevant symbol or range instead of an entire file;
- repeated evidence is referenced rather than injected again; and
- post-tool bookkeeping remains silent, preventing duplicate summaries from inflating every later context window.

## Plain-language explanation

Without ContextGuard, large command outputs remain in the conversation and are paid for again as the task continues. ContextGuard keeps the full evidence locally but gives Codex the smallest useful view. In this benchmark, Codex reached the same verified solution using **149,907 fewer input tokens** and **23,546 fewer tool-output bytes**.

## Trust note

This is a valid real Codex CLI A/B result, not a synthetic token estimate. Both arms completed successfully and passed the same hidden acceptance checks. It is still one paired run, so results will vary by repository, task, model behavior, and how much noisy tool output the workflow produces. Codex subscription quota accounting is not exposed by the CLI; the **1.74x** and **2.64x** figures are capacity equivalents calculated from measured token usage, not guarantees that every subscription limit will last exactly that much longer.

## Short version

> ContextGuard reduced total Codex input by **42.5%** and uncached input by **62.1%** on a real repository repair task, while both runs passed **144 hidden tests**. That equals **1.74x the comparable run capacity from the same total-input budget**—with **60.0% less tool output**, **44.4% fewer commands**, and **31.4% faster completion** in this test.

## Evidence

- Benchmark: `real-codex-bounded-source-inspector-ab`
- Date: 2026-07-12
- ContextGuard build: `0.9.0+codex.20260712125230`
- Git commit containing the runtime fix: `fb573ab`
- Result artifact: `contextguard/benchmarks/results/real-codex-inspect-ab-silent-posthook-2026-07-12/summary.json`
