import json

import pytest

from core.tui.events import EventParseError, load_raw_events, normalize_events


def test_load_jsonl_and_normalize_with_phase_carry_forward(tmp_path):
    path = tmp_path / "replay.jsonl"
    lines = [
        {"type": "on_phase_header", "phase_number": 1},
        {"type": "on_public_action", "speaker": "Ava", "message": "hello"},
        {"type": "on_round_start", "round_number": "2", "scores": {"Ava": "3", "Bryn": 1}},
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")

    raw = load_raw_events(path)
    events = normalize_events(raw)

    assert len(events) == 3
    assert [event.phase for event in events] == [1, 1, 1]
    assert events[1].actor == "Ava"
    assert events[1].text == "hello"
    assert events[2].round == 2
    assert events[2].scores == {"Ava": 3, "Bryn": 1}


def test_load_json_array(tmp_path):
    path = tmp_path / "replay.json"
    payload = [
        {"type": "on_game_intro", "text": "intro", "phase": 0},
        {"type": "on_game_over", "winner_name": "Ava", "phase": 2},
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")

    raw = load_raw_events(path)
    events = normalize_events(raw)

    assert [event.type for event in events] == ["on_game_intro", "on_game_over"]
    assert [event.phase for event in events] == [0, 2]


def test_load_raw_events_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "replay.txt"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(EventParseError, match="Unsupported file extension"):
        load_raw_events(path)


def test_normalize_requires_event_type(tmp_path):
    path = tmp_path / "replay.jsonl"
    path.write_text(json.dumps({"message": "missing type"}) + "\n", encoding="utf-8")

    raw = load_raw_events(path)
    with pytest.raises(EventParseError, match="missing a 'type' field"):
        normalize_events(raw)
