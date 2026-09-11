# ContextGuard multi-task benchmark — 2026-09-11

## Verdict

The broader post-fix live comparison is still workload-dependent, but its pooled result is positive: across **six functional pairs and three larger task types**, ContextGuard used **21.56% fewer total tokens** and the OpenAI Standard API cost proxy was **37.12% lower**. The strict exact-output/capture gate passed in 3/6 pairs. The support workload remains variable, so this is evidence of a savings trend rather than a universal guarantee.

The CI/timezone workload improved strongly; the backend/inventory pair saved API cost while using more total tokens; and the support/concurrency series saved on pooled cost but had a **+10.23% median pair cost**. The website reports those task-level results and retains the earlier **+7.01% pre-fix reference** explicitly as historical context, not as the current headline.

## Post-fix multi-task run

The current routing implementation was exercised with trusted hooks, GPT-5.6 Luna, and low reasoning effort. Each task used the same prompt and fresh fixture for RAW and ContextGuard. All 12 arms passed their fixture validation; 3/6 pairs also passed the stricter exact-output, baseline-shape, and capture-integrity gate. The pooled table includes all six functional pairs, while the gate count stays visible.

| Measure | RAW | ContextGuard | Change |
| --- | ---: | ---: | ---: |
| Total tokens | 1,594,223 | 1,250,429 | **-21.56%** |
| Input tokens | 1,573,660 | 1,228,043 | -21.96% |
| Uncached input tokens | 251,164 | 240,395 | -4.29% |
| API cost proxy | $0.150588 | $0.094695 | **-37.12%** |
| Tool-output bytes | 3,271,753 | 1,111,776 | -66.02% |
| Command executions | 47 | 50 | +6.38% |
| Elapsed time | 472.026s | 542.834s | +15.00% |

Translated through the GPT-6 Astra Standard rate card, the same measured usage is **$7.266034 RAW versus $4.510898 ContextGuard (-37.92%)**. This is a rate translation, not a second Astra execution.

| Task | Functional pairs | Strict gate | Total-token change | API proxy change | Median API change |
| --- | ---: | ---: | ---: | ---: | ---: |
| CI / timezone investigation | 2/2 | 1/2 | -50.04% | -57.35% | -57.35% |
| Support / concurrency investigation | 3/3 | 1/3 | +3.09% pooled | -19.30% pooled | **+10.23%** |
| Backend / inventory reservation | 1/1 | 1/1 | +11.72% | -14.08% | -14.08% |

The support pair that changed the canonical output added the expected v2 `version` field while all hidden tests passed; it was excluded from the strict gate but not from the functional pooled cost sample.

## Post-fix cost-safe routing pilot

The shell-routing fix was then tested in one additional support/concurrency pair with trusted hooks enabled. Both arms completed the fixture validation successfully. The optimized arm reduced the API cost proxy by **46.68%**, total tokens by **10.05%**, and visible tool output by **66.25%**. It used more individual commands, so the strict release gate did not accept this single stochastic pair; this is directional validation of the fix, not a replacement for the multi-pair aggregate above.

| Measure | RAW | Cost-safe ContextGuard | Change |
| --- | ---: | ---: | ---: |
| Total tokens | 299,039 | 268,973 | -10.05% |
| Input tokens | 293,484 | 264,184 | -9.98% |
| API cost proxy | $0.030625 | $0.016328 | **-46.68%** |
| Tool-output bytes | 29,825 | 10,065 | -66.25% |
| Command executions | 6 | 11 | +83.33% |
| Elapsed time | 121.405s | 115.298s | -5.03% |

The fix only automatically captures high-yield noisy segments, leaves exact source reads visible, and refuses to nest an existing `contextguard capture` invocation. Compound shell pipelines that cannot be safely split remain unchanged. The one-pair result is subject to model and order variance and should not be read as a universal savings percentage.

## Scope and quality

- Model: gpt-5.6-luna
- Reasoning effort: low
- Post-fix tasks: 3 large maintenance fixtures
- Post-fix counterbalanced pairs attempted: 6
- Post-fix pairs passing every harness gate: 3/6
- Post-fix quality-green arms: 12/12
- Post-fix pooled aggregate includes all six functionally green pairs; the strict gate count remains separate.
- Each accepted CI pair passed 160/160 hidden tests in both arms.
- The accepted support pair passed 144/144 hidden tests in both arms.

The earlier pre-fix run had 5 pairs, 3 accepted pairs, and 8/10 quality-green arms. One additional support pair passed fixture quality but failed the strict baseline-command gate; one pair failed fixture quality in both arms. Its +7.01% API result is retained below as a historical reference.

## Pre-fix accepted-gate reference

| Measure | RAW | ContextGuard | Change |
| --- | ---: | ---: | ---: |
| Total tokens | 1,015,444 | 940,023 | -7.43% |
| Uncached input tokens | 197,077 | 130,382 | -33.84% |
| API cost proxy | $0.097384 | $0.104209 | +7.01% |
| Tool-output bytes | 1,185,553 | 2,216,702 | +86.98% |
| Command executions | 26 | 24 | -7.69% |
| Elapsed time | 259.442s | 252.546s | -2.66% |

## Pre-fix task split

| Task | Accepted pairs | Total-token change | Uncached-input change | API proxy change |
| --- | ---: | ---: | ---: | ---: |
| CI / timezone investigation | 2/2 | -19.38% | -40.05% | -13.27% |
| Support / concurrency investigation | 1/3 | +42.77% | -20.80% | +88.68% |

The pre-fix CI task used medians of 410,104 RAW versus 330,643 ContextGuard total tokens. The pre-fix support task used medians of 195,236 RAW versus 278,737 ContextGuard total tokens.

## Pricing basis

Costs use the OpenAI Standard API rate card, selected per measured turn using the 272,000-token short/long context boundary. The live test used GPT-5.6 Luna:

| Model/context | Input | Cached input | Cache write | Output |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.6 Luna · short | $0.20/M | $0.02/M | $0.25/M | $1.20/M |
| GPT-5.6 Luna · long | $0.40/M | $0.04/M | $0.50/M | $1.80/M |
| GPT-6 Astra · short | $10/M | $1/M | $12.50/M | $50/M |
| GPT-6 Astra · long | $20/M | $2/M | $25/M | $75/M |

Applying the GPT-6 Astra Standard rates to the **pre-fix accepted-gate** usage gives an equivalent proxy of **$4.738319 RAW versus $5.042843 ContextGuard (+6.43%)**. The current post-fix six-pair translation is reported above as **$7.266034 RAW versus $4.510898 ContextGuard (-37.92%)**. These are model-rate translations, not Astra executions.

Official source: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), verified 2026-09-11.

## Interpretation

The capture and evidence path is valuable on the CI-style task and sharply reduces visible tool output across all three task types. The post-fix pooled sample also lowers the API proxy, but support and backend show that fewer tool bytes do not automatically mean fewer total tokens or faster completion: the model can choose a different exploration path, issue more commands, or generate more response tokens. ContextGuard should keep measuring per-task quality and cost before treating the pooled percentage as guaranteed.

Codex subscription billing and private usage-limit accounting are not exposed by the Codex CLI. The API figures above are transparent cost proxies only.
