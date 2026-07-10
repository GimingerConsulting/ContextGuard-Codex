from contextguard.history_pack import archive_index_summary, record_archive_metadata


def test_record_archive_metadata_tracks_repeated_fingerprints(tmp_path):
    record_archive_metadata(
        tmp_path,
        archive_path="/tmp/first.summary.json",
        fingerprint="fp-1",
        raw_bytes=5000,
    )
    record_archive_metadata(
        tmp_path,
        archive_path="/tmp/second.summary.json",
        fingerprint="fp-1",
        raw_bytes=5000,
    )
    summary = archive_index_summary(tmp_path)
    assert summary["entries"] == 1
    assert summary["repeated_fingerprints"] == 1