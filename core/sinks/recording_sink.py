from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from core.sinks.game_sink import GameEventSink, Speaker


class RecordingGameEventSink(GameEventSink):
    """
    Records all emitted game events to JSONL for replay, optionally forwarding
    events to another sink (for example ConsoleGameEventSink).
    """

    def __init__(self, output_path: str, delegate: GameEventSink | None = None):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.output_path.open("a", encoding="utf-8")
        self.delegate = delegate

        self.phase_number = 0
        self.round_number = 0
        self.turn_number = 0

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.close()

    def on_game_intro(self, message: str) -> None:
        self._emit("on_game_intro", text=message)
        self._forward("on_game_intro", message)

    def on_game_over(self, winner_name: str) -> None:
        self._emit("on_game_over", winner_name=winner_name, text=winner_name)
        self._forward("on_game_over", winner_name)

    def on_phase_header(self, phase_number: int) -> None:
        self.phase_number = phase_number
        self.round_number = 0
        self.turn_number = 0
        self._emit("on_phase_header", phase_number=phase_number)
        self._forward("on_phase_header", phase_number)

    def on_phase_intro(self, host_text: str, summary_text: str) -> None:
        self._emit(
            "on_phase_intro",
            host_text=host_text,
            summary_text=summary_text,
            text=host_text,
            summary=summary_text,
        )
        self._forward("on_phase_intro", host_text, summary_text)

    def on_round_start(self, round_number: int, scores: dict[str, int]) -> None:
        self.round_number = round_number
        self.turn_number = 0
        self._emit("on_round_start", round_number=round_number, scores=dict(scores))
        self._forward("on_round_start", round_number, scores)

    def on_round_summary(self, summary: str) -> None:
        self._emit("on_round_summary", summary=summary, text=summary)
        self._forward("on_round_summary", summary)

    def on_turn_header(self, turn_number: int) -> None:
        self.turn_number = turn_number
        self._emit("on_turn_header", turn_number=turn_number)
        self._forward("on_turn_header", turn_number)

    def on_public_action(self, speaker: Speaker, message: str, color: str = "") -> None:
        self._emit(
            "on_public_action",
            speaker=self._speaker_name(speaker),
            message=message,
            color=color,
            text=message,
        )
        self._forward("on_public_action", speaker, message, color)

    def on_private_thought(self, speaker: Speaker, message: str) -> None:
        self._emit(
            "on_private_thought",
            speaker=self._speaker_name(speaker),
            message=message,
            text=message,
        )
        self._forward("on_private_thought", speaker, message)

    def on_inner_workings(self, speaker: Speaker, inner_workings: list[tuple[str, Any]], override: bool = False) -> None:
        serialized = [
            {"key": str(key), "value": value}
            for key, value in inner_workings
        ]
        self._emit(
            "on_inner_workings",
            speaker=self._speaker_name(speaker),
            inner=serialized,
            override=override,
        )
        if self.delegate is not None and hasattr(self.delegate, "on_inner_workings"):
            getattr(self.delegate, "on_inner_workings")(speaker, inner_workings, override)

    def delay(self, delay: float = 0.0) -> None:
        self._forward("delay", delay)

    def on_points_update(self, points: dict[str, int]) -> None:
        scoreboard = dict(points)
        self._emit("on_points_update", points=scoreboard, scores=scoreboard)
        self._forward("on_points_update", scoreboard)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _emit(self, event_type: str, **payload: Any) -> None:
        event = {
            "type": event_type,
            "phase": self.phase_number,
            "round_number": self.round_number,
            "turn_number": self.turn_number,
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        json.dump(event, self._handle, ensure_ascii=True)
        self._handle.write("\n")
        self._handle.flush()

    def _forward(self, method: str, *args: Any) -> None:
        if self.delegate is None:
            return
        fn = getattr(self.delegate, method, None)
        if callable(fn):
            fn(*args)

    def _speaker_name(self, speaker: Speaker) -> str:
        if isinstance(speaker, BaseAgent):
            return speaker.name
        return str(speaker)
