from core.sinks.recording_sink import RecordingGameEventSink
from core.tui.events import events_for_phase, load_raw_events, normalize_events, phase_numbers


def test_recorded_replay_is_consumable_by_tui_pipeline(tmp_path):
    replay_path = tmp_path / "pipeline.jsonl"
    sink = RecordingGameEventSink(str(replay_path), delegate=None)

    sink.on_game_intro("intro")
    sink.on_phase_header(1)
    sink.on_phase_intro("host phase 1", "summary phase 1")
    sink.on_round_start(1, {"Ava": 0, "Bryn": 0})
    sink.on_turn_header(1)
    sink.on_public_action("Ava", "hello")
    sink.on_private_thought("Bryn", "hmm")
    sink.on_round_summary("phase 1 done")

    sink.on_phase_header(2)
    sink.on_phase_intro("host phase 2", "summary phase 2")
    sink.on_round_start(2, {"Ava": 3})
    sink.on_public_action("SYSTEM", "Bryn eliminated")
    sink.on_game_over("Ava")
    sink.close()

    raw = load_raw_events(replay_path)
    events = normalize_events(raw)

    assert len(events) == 13
    assert phase_numbers(events) == [0, 1, 2]

    phase_1_events = events_for_phase(events, 1)
    phase_2_events = events_for_phase(events, 2)

    assert any(event.type == "on_private_thought" for event in phase_1_events)
    assert any(event.type == "on_game_over" for event in phase_2_events)

    final_event = events[-1]
    assert final_event.type == "on_game_over"
    assert final_event.phase == 2
    assert final_event.payload["winner_name"] == "Ava"
