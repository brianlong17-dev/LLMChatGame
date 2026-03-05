import json

from core.sinks.recording_sink import RecordingGameEventSink


class FakeDelegate:
    def __init__(self):
        self.calls = []

    def on_game_intro(self, message):
        self.calls.append(("on_game_intro", message))

    def on_game_over(self, winner_name):
        self.calls.append(("on_game_over", winner_name))

    def on_phase_header(self, phase_number):
        self.calls.append(("on_phase_header", phase_number))

    def on_phase_intro(self, host_text, summary_text):
        self.calls.append(("on_phase_intro", host_text, summary_text))

    def on_round_start(self, round_number, scores):
        self.calls.append(("on_round_start", round_number, dict(scores)))

    def on_round_summary(self, summary):
        self.calls.append(("on_round_summary", summary))

    def on_turn_header(self, turn_number):
        self.calls.append(("on_turn_header", turn_number))

    def on_public_action(self, speaker, message, color=""):
        self.calls.append(("on_public_action", speaker, message, color))

    def on_private_thought(self, speaker, message):
        self.calls.append(("on_private_thought", speaker, message))

    def on_inner_workings(self, speaker, inner_workings, override=False):
        self.calls.append(("on_inner_workings", speaker, list(inner_workings), override))

    def on_points_update(self, points):
        self.calls.append(("on_points_update", dict(points)))

    def delay(self, delay=0.0):
        self.calls.append(("delay", delay))


def test_recording_sink_writes_jsonl_and_forwards(tmp_path):
    output = tmp_path / "replay.jsonl"
    delegate = FakeDelegate()
    sink = RecordingGameEventSink(str(output), delegate=delegate)

    sink.on_game_intro("welcome")
    sink.on_phase_header(1)
    sink.on_phase_intro("host", "summary")
    sink.on_round_start(2, {"Ava": 5, "Bryn": 3})
    sink.on_turn_header(3)
    sink.on_public_action("Ava", "public message", "GREEN")
    sink.on_private_thought("Bryn", "private message")
    sink.on_inner_workings("Bryn", [("risk_score", 0.42)], override=True)
    sink.on_points_update({"Ava": 6, "Bryn": 2})
    sink.on_round_summary("round done")
    sink.delay(0.01)
    sink.on_game_over("Ava")
    sink.close()

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    types = [row["type"] for row in rows]

    assert types == [
        "on_game_intro",
        "on_phase_header",
        "on_phase_intro",
        "on_round_start",
        "on_turn_header",
        "on_public_action",
        "on_private_thought",
        "on_inner_workings",
        "on_points_update",
        "on_round_summary",
        "on_game_over",
    ]

    public = rows[5]
    assert public["phase"] == 1
    assert public["round_number"] == 2
    assert public["turn_number"] == 3
    assert public["speaker"] == "Ava"
    assert public["message"] == "public message"

    inner = rows[7]
    assert inner["speaker"] == "Bryn"
    assert inner["override"] is True
    assert inner["inner"] == [{"key": "risk_score", "value": 0.42}]

    points_update = rows[8]
    assert points_update["points"] == {"Ava": 6, "Bryn": 2}
    assert points_update["scores"] == {"Ava": 6, "Bryn": 2}

    assert rows[-1]["winner_name"] == "Ava"
    assert all("ts" in row for row in rows)

    forwarded_methods = [call[0] for call in delegate.calls]
    assert "on_public_action" in forwarded_methods
    assert "on_inner_workings" in forwarded_methods
    assert "on_points_update" in forwarded_methods
    assert "delay" in forwarded_methods
