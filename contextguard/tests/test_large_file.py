import json
from pathlib import Path

from contextguard.large_file import summarize_large_file


def test_large_json_summarization(tmp_path: Path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps([{"a": 1, "b": None}, {"a": 2, "c": "x"}]))
    result = summarize_large_file(path)
    assert result["records"] == 2
    assert "a" in result["observed_keys"]


def test_large_csv_summarization(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("name,value\nA,1\nB,\n")
    result = summarize_large_file(path)
    assert result["records"] == 2
    assert result["null_counts"]["value"] == 1


def test_targeted_line_and_match_context(tmp_path: Path):
    path = tmp_path / "app.log"
    path.write_text("one\ntwo\nERROR bad\nfour\n")
    result = summarize_large_file(path, contains="ERROR", before=1, after=1, lines="2:3")
    assert result["matches"][0]["context"] == ["two", "ERROR bad", "four"]
    assert [line["line"] for line in result["selected_lines"]] == [2, 3]


def test_log_summary_groups_severity_and_redacts_variable_values(tmp_path: Path):
    path = tmp_path / "service.log"
    path.write_text(
        "INFO request id=100 status=200\n"
        "ERROR database timeout host=10.0.0.5 password=secret-value duration=31ms\n"
        "ERROR database timeout host=10.0.0.6 password=other-value duration=44ms\n",
        encoding="utf-8",
    )

    result = summarize_large_file(path)

    assert result["severity_counts"] == {"INFO": 1, "ERROR": 2}
    assert len(result["error_signatures"]) == 1
    assert "secret-value" not in result["error_signatures"][0]
