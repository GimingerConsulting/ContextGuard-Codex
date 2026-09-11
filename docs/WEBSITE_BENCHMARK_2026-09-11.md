# ContextGuard multi-task benchmark — 2026-09-11

## Verdict

The fresh live comparison is workload-dependent. On the strict accepted-gate aggregate, ContextGuard used **7.43% fewer total tokens** and **33.84% less uncached input**, but the OpenAI Standard API cost proxy was **7.01% higher** because one large support/concurrency task expanded its context and crossed the long-context pricing threshold.

The CI/timezone workload improved. The support/concurrency workload regressed. The website therefore reports both results instead of presenting one blanket savings claim.

## Scope and quality

- Model: gpt-5.6-luna
- Reasoning effort: low
- Tasks: 2 large maintenance fixtures
- Counterbalanced pairs attempted: 5
- Pairs passing every harness gate: 3
- Quality-green arms: 8/10
- Aggregate includes only the 3 fully accepted pairs.
- Each accepted CI pair passed 160/160 hidden tests in both arms.
- The accepted support pair passed 144/144 hidden tests in both arms.

One additional support pair passed the fixture quality checks but failed the strict baseline-command gate. One support pair failed fixture quality in both arms. Neither is included in the aggregate.

## Accepted-gate aggregate

| Measure | RAW | ContextGuard | Change |
| --- | ---: | ---: | ---: |
| Total tokens | 1,015,444 | 940,023 | -7.43% |
| Uncached input tokens | 197,077 | 130,382 | -33.84% |
| API cost proxy | $0.097384 | $0.104209 | +7.01% |
| Tool-output bytes | 1,185,553 | 2,216,702 | +86.98% |
| Command executions | 26 | 24 | -7.69% |
| Elapsed time | 259.442s | 252.546s | -2.66% |

## Task split

| Task | Accepted pairs | Total-token change | Uncached-input change | API proxy change |
| --- | ---: | ---: | ---: | ---: |
| CI / timezone investigation | 2/2 | -19.38% | -40.05% | -13.27% |
| Support / concurrency investigation | 1/3 | +42.77% | -20.80% | +88.68% |

The CI task used medians of 410,104 RAW versus 330,643 ContextGuard total tokens. The support task used medians of 195,236 RAW versus 278,737 ContextGuard total tokens.

## Pricing basis

Costs use the OpenAI Standard API rate card, selected per measured turn using the 272,000-token short/long context boundary. The live test used GPT-5.6 Luna:

| Model/context | Input | Cached input | Cache write | Output |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Luna · short | $0.20/M | $0.02/M | $0.25/M | $1.20/M |
| GPT-5.6 Luna · long | $0.40/M | $0.04/M | $0.50/M | $1.80/M |
| GPT-6 Astra · short | $10/M | $1/M | $12.50/M | $50/M |
| GPT-6 Astra · long | $20/M | $2/M | $25/M | $75/M |

Applying the GPT-6 Astra Standard rates to the same accepted-gate usage gives an equivalent proxy of **$4.738319 RAW versus $5.042843 ContextGuard (+6.43%)**. This is a model-rate translation, not a second Astra execution.

Official source: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), verified 2026-09-11.

## Interpretation

The capture and evidence path is valuable on the CI-style task, where it reduced input, uncached input, commands and cost while preserving hidden-test quality. The support trace shows that compaction alone is not sufficient: a model can choose a different exploration path, emit more output, or cross a context-pricing boundary. ContextGuard should keep measuring per-task quality and cost before treating a global percentage as guaranteed.

Codex subscription billing and private usage-limit accounting are not exposed by the Codex CLI. The API figures above are transparent cost proxies only.
