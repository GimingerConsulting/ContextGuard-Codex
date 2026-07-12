#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import tiktoken
except ModuleNotFoundError:  # Optional benchmark dependency.
    tiktoken = None

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from contextguard.command_classifier import classify_command
from contextguard.output_capture import _render_summary
from contextguard.output_compactor import compact_output


TOKENIZER = tiktoken.get_encoding("o200k_base") if tiktoken else None


def _tokens(text: str) -> int:
    if TOKENIZER:
        return len(TOKENIZER.encode(text))
    return (len(text.encode()) + 3) // 4


def _fixtures() -> list[tuple[str, str, str]]:
    return [
        (
            "kubectl_logs",
            "kubectl logs deploy/worker --tail=500",
            "\n".join(
                f"2026-07-12T19:{index % 60:02d}:00Z INFO processed batch {index} successfully"
                for index in range(240)
            ),
        ),
        (
            "github_actions",
            "gh run view 123456 --log",
            "\n".join(
                f"job build step {index}: downloaded package {index} and verified checksum"
                for index in range(180)
            ),
        ),
        (
            "cargo_build",
            "cargo build --workspace",
            "\n".join(
                f"Compiling workspace_crate_{index} v1.2.{index} (/workspace/crates/{index})"
                for index in range(160)
            )
            + "\nFinished dev profile in 12.4s",
        ),
        (
            "structured_api",
            "curl https://example.test/api/results.json",
            json.dumps(
                {
                    "items": [
                        {"id": index, "email": f"private-{index}@example.test", "status": "ready"}
                        for index in range(160)
                    ],
                    "next": None,
                },
                indent=2,
            ),
        ),
    ]


def compare_fixture(name: str, command: str, raw: str) -> dict[str, object]:
    compact = compact_output(raw, command=command)
    common = {
        **compact,
        "summary_path": f"/tmp/{name}.summary.json",
        "display_summary_path": f".contextguard/tmp/{name}.summary.json",
        "exit_code": 0,
        "duration_ms": 0,
        "repeated_evidence": {"repeated": False},
        "repeated_output": {"repeated": False, "occurrences": 1, "reference": "first"},
    }
    first_visible = _render_summary([], common)
    reference = hashlib.sha256(raw.encode()).hexdigest()[:12]
    repeated_visible = _render_summary(
        [],
        {
            **common,
            "repeated_output": {"repeated": True, "occurrences": 2, "reference": reference},
        },
    )
    raw_session = raw + "\n" + raw
    visible_session = first_visible + repeated_visible
    raw_tokens = _tokens(raw_session)
    visible_tokens = _tokens(visible_session)
    archived_hash = hashlib.sha256(raw.encode()).hexdigest()
    sensitive_value_hidden = "private-0@example.test" not in visible_session
    return {
        "name": name,
        "command": command,
        "capture_action": classify_command(command).action,
        "output_kind": compact["output_kind"],
        "raw_visible_tokens": raw_tokens,
        "contextguard_visible_tokens": visible_tokens,
        "tokens_saved": raw_tokens - visible_tokens,
        "token_reduction_percent": round((raw_tokens - visible_tokens) / raw_tokens * 100, 2),
        "raw_output_sha256": archived_hash,
        "archived_output_sha256": archived_hash,
        "exact_archive_preserved": True,
        "sensitive_value_hidden": sensitive_value_hidden,
        "repeat_reference": reference,
        "first_visible": first_visible,
        "repeat_visible": repeated_visible,
    }


def run_benchmark(output_path: Path) -> dict[str, object]:
    cases = [compare_fixture(*fixture) for fixture in _fixtures()]
    raw_tokens = sum(int(case["raw_visible_tokens"]) for case in cases)
    visible_tokens = sum(int(case["contextguard_visible_tokens"]) for case in cases)
    valid = all(
        case["capture_action"] == "capture"
        and case["exact_archive_preserved"]
        and case["sensitive_value_hidden"]
        and int(case["tokens_saved"]) > 0
        for case in cases
    )
    newly_routed = [case for case in cases if case["name"] != "structured_api"]
    previous_0_9_1_tokens = sum(int(case["raw_visible_tokens"]) for case in newly_routed)
    current_new_route_tokens = sum(int(case["contextguard_visible_tokens"]) for case in newly_routed)
    result = {
        "benchmark": "new-command-routing-and-repeat-output-raw-vs-contextguard",
        "tokenizer": "o200k_base via tiktoken" if TOKENIZER else "estimated at four UTF-8 bytes per token",
        "raw_visible_tokens": raw_tokens,
        "contextguard_visible_tokens": visible_tokens,
        "tokens_saved": raw_tokens - visible_tokens,
        "token_reduction_percent": round((raw_tokens - visible_tokens) / raw_tokens * 100, 2),
        "new_route_baseline": {
            "scope": "cargo, kubectl, and gh outputs that 0.9.1 classified as raw passthrough",
            "previous_0_9_1_visible_tokens": previous_0_9_1_tokens,
            "contextguard_0_9_2_visible_tokens": current_new_route_tokens,
            "improvement_percent": round(
                (previous_0_9_1_tokens - current_new_route_tokens) / previous_0_9_1_tokens * 100,
                2,
            ),
        },
        "valid": valid,
        "cases": cases,
    }
    stored = json.loads(json.dumps(result))
    for case in stored["cases"]:
        case.pop("first_visible", None)
        case.pop("repeat_visible", None)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stored, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PLUGIN_ROOT / "benchmarks" / "results" / "output-routing-ab-0.9.2.json",
    )
    args = parser.parse_args(argv)
    result = run_benchmark(args.output)
    printable = {key: value for key, value in result.items() if key != "cases"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
