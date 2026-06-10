# ContextGuard Benchmark Harness

Run:

```bash
PYTHONPATH=. python3 benchmarks/run_benchmarks.py
```

The harness creates separate baseline and optimized copies for ten scenarios: a trivial change, medium feature, complex failure, verbose test suite, large JSON analysis, repeated errors, long session, unchanged restart, partial-change restart, and large repository.

Each pair uses the same command and starting content. Success requires the same exit code and repository-state hash, excluding ContextGuard's local `.contextguard/` state. The JSON records measured output bytes and duration, estimated token reduction, ContextGuard overhead, and semantic final-response quality.

This is deterministic local tooling, not a complete Codex usage measurement. Token values use a labeled four-bytes-per-token estimate. Real-world claims require controlled Codex A/B runs with the same prompt, model, reasoning level, environment, tools and validation criteria.

## Real Codex Hard A/B

Run the opt-in real model benchmark:

```bash
python3 benchmarks/real_codex_ab.py --self-check
python3 benchmarks/real_codex_ab.py --run
```

The harness creates two identical settlement repositories, uses isolated Codex homes with the same authentication, runs `gpt-5.5` at medium reasoning, parses exact `turn.completed.usage` fields, and validates 130 cases plus canonical CLI output. The optimized copy alone is initialized with ContextGuard and project hooks.

The June 10, 2026 result is stored in `benchmarks/results/real-codex-hard-ab-2026-06-10.json`. No rerun was accepted: `codex exec` 0.128.0 and 0.139.0 completed both repositories but dispatched zero ContextGuard hooks. The harness now rejects any optimized trial without observed hook invocations and output compaction. See upstream Codex issues 25875, 26383 and 26452.

## Direct Output A/B

Run `python3 benchmarks/output_ab.py` to compare the exact same hard 130-failure pytest output as fully visible RAW output and as the real ContextGuard PostToolUse response. The test counts visible bytes and `o200k_base` tokens, measures median processing time, verifies that the complete archived output is byte-identical, and requires the compact response to retain the test summary and concrete failed-test names.

The June 10 result in `benchmarks/results/output-ab-2026-06-10.json` measured 20,650 RAW tokens versus 543 ContextGuard tokens, saving 20,107 tokens or 97.37%, with 42.5 ms median additional processing time across eleven samples.
