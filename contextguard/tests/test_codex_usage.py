import json
from pathlib import Path

from contextguard.codex_usage import calculate_turn_cost, current_codex_usage, parse_codex_session


def _write_session(path: Path, root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {"type": "session_meta", "payload": {"id": "session-1", "cwd": str(root)}},
        {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "medium"}},
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 1_000_000,
                        "cached_input_tokens": 800_000,
                        "cache_write_input_tokens": 100_000,
                        "output_tokens": 10_000,
                        "reasoning_output_tokens": 2_000,
                        "total_tokens": 1_010_000,
                    },
                    "last_token_usage": {
                        "input_tokens": 1_000_000,
                        "cached_input_tokens": 800_000,
                        "cache_write_input_tokens": 100_000,
                        "output_tokens": 10_000,
                        "reasoning_output_tokens": 2_000,
                        "total_tokens": 1_010_000,
                    },
                },
            },
        },
        {"type": "turn_context", "payload": {"model": "gpt-5.6-luna", "effort": "low"}},
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 1_010_000,
                        "cached_input_tokens": 808_000,
                        "cache_write_input_tokens": 100_000,
                        "output_tokens": 11_000,
                        "reasoning_output_tokens": 2_100,
                        "total_tokens": 1_021_000,
                    },
                    "last_token_usage": {
                        "input_tokens": 10_000,
                        "cached_input_tokens": 8_000,
                        "cache_write_input_tokens": 0,
                        "output_tokens": 1_000,
                        "reasoning_output_tokens": 100,
                        "total_tokens": 11_000,
                    },
                },
            },
        },
    ]
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")


def test_parse_codex_session_attributes_tokens_and_cost_by_model(tmp_path):
    session = tmp_path / "session.jsonl"
    _write_session(session, tmp_path)

    report = parse_codex_session(session)

    assert report["models_used"] == ["gpt-5.6-sol", "gpt-5.6-luna"]
    assert report["input_tokens"] == 1_010_000
    assert report["cached_input_tokens"] == 808_000
    assert report["reasoning_output_tokens"] == 2_100
    assert report["total_tokens"] == 1_021_000
    assert report["model_breakdown"][0]["long_context_turns"] == 1
    assert report["model_breakdown"][1]["short_context_turns"] == 1
    assert report["api_cost_usd"] == 3.5088


def test_current_usage_selects_latest_session_for_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    codex_home = tmp_path / "codex-home"
    session = codex_home / "sessions" / "2026" / "07" / "22" / "rollout.jsonl"
    _write_session(session, project)

    report = current_codex_usage(project, codex_home=codex_home)

    assert report["available"] is True
    assert report["session_id"] == "session-1"


def test_unknown_model_keeps_exact_tokens_but_marks_cost_incomplete(tmp_path):
    session = tmp_path / "unknown.jsonl"
    _write_session(session, tmp_path)
    text = session.read_text(encoding="utf-8").replace("gpt-5.6-sol", "future-model")
    session.write_text(text, encoding="utf-8")

    report = parse_codex_session(session)

    assert report["total_tokens"] == 1_021_000
    assert report["api_cost_usd"] is None
    assert report["api_cost_complete"] is False


def test_gpt56_cache_write_and_long_context_rates_are_applied():
    usage = {
        "input_tokens": 300_000,
        "cached_input_tokens": 100_000,
        "cache_write_input_tokens": 100_000,
        "output_tokens": 10_000,
    }

    cost, context_class = calculate_turn_cost("gpt-5.6-terra", usage)

    assert context_class == "long"
    assert cost == 1.4
