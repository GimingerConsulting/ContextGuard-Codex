#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from benchmarks.real_codex_support_ab import PROMPT, create_fixture
from contextguard.source_inspector import inspect_sources
from contextguard.task_evidence import build_task_evidence
from contextguard.utils import estimate_tokens


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_ORIENTATION_COMMANDS = 8
PREVIOUS_ORIENTATION_OUTPUT_BYTES = 8_590
PREVIOUS_STRUCTURED_DISCOVERY_BYTES = 1_600


def run_benchmark() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="contextguard-evidence-packet-") as tmp:
        project = create_fixture(Path(tmp) / "fixture")
        packet = build_task_evidence(project, PROMPT, token_limit=420)
        structured = inspect_sources(
            project,
            [
                "data/production.log",
                "data/warehouse-export.jsonl",
                "scenario.json",
                "legacy-db.json",
            ],
        )
        structured_text = json.dumps(structured, separators=(",", ":"), sort_keys=True)
    packet_bytes = len(packet.encode())
    structured_bytes = len(structured_text.encode())
    combined_bytes = packet_bytes + structured_bytes
    return {
        "benchmark": "task-evidence-and-structured-inspect-mechanism-ab",
        "previous_live_orientation_commands": PREVIOUS_ORIENTATION_COMMANDS,
        "previous_live_orientation_output_bytes": PREVIOUS_ORIENTATION_OUTPUT_BYTES,
        "previous_live_structured_discovery_bytes": PREVIOUS_STRUCTURED_DISCOVERY_BYTES,
        "task_evidence_bytes": packet_bytes,
        "task_evidence_tokens_estimate": estimate_tokens(packet),
        "structured_inspect_bytes": structured_bytes,
        "combined_visible_bytes": combined_bytes,
        "combined_reduction_vs_previous_orientation_percent": round(
            (PREVIOUS_ORIENTATION_OUTPUT_BYTES - combined_bytes) * 100 / PREVIOUS_ORIENTATION_OUTPUT_BYTES,
            2,
        ),
        "packet_contains_ticket": "SUPPORT_TICKET.md" in packet,
        "structured_file_count": structured["file_count"],
        "structured_values_hidden": all(
            value not in structured_text
            for value in ("secret", "password", "token-value", "private-value")
        ),
        "limitations": [
            "Deterministic mechanism benchmark; it does not prove that a stochastic Codex run will skip every prior orientation command.",
            "The post-change live Codex pair was quota-rejected at zero tokens and is invalid.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PLUGIN_ROOT / "benchmarks/results/evidence-packet-ab-2026-07-11.json",
    )
    args = parser.parse_args(argv)
    result = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(
        not result["packet_contains_ticket"]
        or result["structured_file_count"] != 4
        or result["combined_visible_bytes"] >= PREVIOUS_ORIENTATION_OUTPUT_BYTES
    )


if __name__ == "__main__":
    raise SystemExit(main())
