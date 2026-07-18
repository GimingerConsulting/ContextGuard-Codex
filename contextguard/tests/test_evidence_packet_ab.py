from benchmarks.evidence_packet_ab import PREVIOUS_ORIENTATION_OUTPUT_BYTES, run_benchmark


def test_evidence_packet_mechanism_reduces_orientation_payload():
    result = run_benchmark()

    assert result["packet_contains_ticket"] is True
    assert result["packet_contains_service_dependency"] is True
    assert result["packet_contains_reserve_body"] is True
    assert result["packet_contains_reuse_contract"] is True
    assert result["task_evidence_bytes"] < PREVIOUS_ORIENTATION_OUTPUT_BYTES
    assert result["snapshot_unchanged_mode"] == "unchanged"
    assert result["snapshot_delta_mode"] == "delta"
    assert result["snapshot_repeat_reduction_percent"] > 80
