#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from benchmarks.real_codex_support_ab import PROMPT, create_fixture
from contextguard.snapshot_store import snapshot_source
from contextguard.task_evidence import build_task_evidence
from contextguard.utils import estimate_tokens


PREVIOUS_ORIENTATION_COMMANDS = 16
PREVIOUS_ORIENTATION_OUTPUT_BYTES = 13_325


def run_benchmark() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="contextguard-evidence-packet-") as tmp:
        project = create_fixture(Path(tmp) / "fixture")
        packet = build_task_evidence(project, PROMPT, token_limit=760)
        first_snapshot = snapshot_source(project, "inventory/service.py")
        unchanged_snapshot = snapshot_source(project, "inventory/service.py")
        service = project / "inventory/service.py"
        service.write_text(service.read_text().replace("record = self.records[sku]", "record = self.records[sku]  # guarded"))
        delta_snapshot = snapshot_source(project, "inventory/service.py")
    packet_bytes = len(packet.encode())
    snapshot_repeat_bytes = len(str(unchanged_snapshot["rendered"]).encode())
    snapshot_delta_bytes = len(str(delta_snapshot["rendered"]).encode())
    return {
        "benchmark": "dependency-working-set-and-snapshot-delta-mechanism-ab",
        "previous_live_orientation_commands": PREVIOUS_ORIENTATION_COMMANDS,
        "previous_live_orientation_output_bytes": PREVIOUS_ORIENTATION_OUTPUT_BYTES,
        "task_evidence_bytes": packet_bytes,
        "task_evidence_tokens_estimate": estimate_tokens(packet),
        "working_set_reduction_vs_0_9_2_pre_edit_output_percent": round(
            (PREVIOUS_ORIENTATION_OUTPUT_BYTES - packet_bytes) * 100 / PREVIOUS_ORIENTATION_OUTPUT_BYTES,
            2,
        ),
        "packet_contains_ticket": "SUPPORT_TICKET.md" in packet,
        "packet_contains_service_dependency": "implementation inventory/service.py" in packet,
        "packet_contains_reserve_body": "def reserve" in packet,
        "packet_contains_reuse_contract": "do not reread unchanged listed files" in packet,
        "snapshot_first_mode": first_snapshot["mode"],
        "snapshot_unchanged_mode": unchanged_snapshot["mode"],
        "snapshot_delta_mode": delta_snapshot["mode"],
        "snapshot_repeat_bytes": snapshot_repeat_bytes,
        "snapshot_delta_bytes": snapshot_delta_bytes,
        "snapshot_repeat_reduction_percent": round(
            (len(str(first_snapshot["rendered"]).encode()) - snapshot_repeat_bytes)
            * 100
            / len(str(first_snapshot["rendered"]).encode()),
            2,
        ),
        "limitations": [
            "Deterministic mechanism benchmark; the paid multi-pair Codex A/B remains the release gate.",
            "The working-set comparison uses the measured median pre-edit output from the accepted 0.9.2 three-pair run.",
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
        or not result["packet_contains_service_dependency"]
        or not result["packet_contains_reserve_body"]
        or result["task_evidence_bytes"] >= PREVIOUS_ORIENTATION_OUTPUT_BYTES
        or result["snapshot_unchanged_mode"] != "unchanged"
        or result["snapshot_delta_mode"] != "delta"
    )


if __name__ == "__main__":
    raise SystemExit(main())
