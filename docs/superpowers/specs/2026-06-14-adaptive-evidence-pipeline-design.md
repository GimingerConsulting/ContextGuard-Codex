# Adaptive Evidence Pipeline Design

## Goal

Reduce model-visible tool output, uncached input, redundant commands and repeated exploration while preserving the same externally validated solution quality as RAW Codex.

## Architecture

ContextGuard will turn captured command output into a structured evidence envelope. The envelope retains decisive facts such as exit status, test totals, failed tests, unique errors, source locations and archive paths while omitting repeated framing and low-value lines. Every full output remains available for targeted escalation.

Session state will track command families, exact reads, output fingerprints and validation outcomes. Advice will be emitted only when it supplies a concrete lower-cost next action. Repeated equivalent output will reference the prior evidence instead of retransmitting it.

## Progressive Disclosure

The default response is the smallest evidence set that remains actionable. ContextGuard escalates locally when output is ambiguous, contradictory, unsuccessful without a diagnostic, explicitly requested, or required for final validation. Escalation reveals additional evidence or a bounded archive slice; it never disables protection for the entire task.

## Quality Boundary

No optimization is accepted unless RAW and ContextGuard satisfy the same public and hidden behavioral checks. Security-sensitive work, migrations, failed validations and unresolved errors retain enough evidence to diagnose and verify correctness.

## Measurement

Primary metrics are solution-quality equivalence and uncached input tokens. Secondary metrics are total input, model-visible tool bytes, command count, generated tokens and elapsed time. Counterbalanced multi-run benchmarks are required because model exploration and prompt-cache behavior are stochastic.

## Scope

This release adds structured evidence rendering, repeated-output suppression, actionable command guidance and adaptive escalation metadata. It does not claim control over OpenAI subscription quota accounting or deterministic LLM behavior.
