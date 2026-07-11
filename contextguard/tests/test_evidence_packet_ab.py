from benchmarks.evidence_packet_ab import PREVIOUS_ORIENTATION_OUTPUT_BYTES, run_benchmark


def test_evidence_packet_mechanism_reduces_orientation_payload():
    result = run_benchmark()

    assert result["packet_contains_ticket"] is True
    assert result["structured_file_count"] == 4
    assert result["structured_values_hidden"] is True
    assert result["combined_visible_bytes"] < PREVIOUS_ORIENTATION_OUTPUT_BYTES
