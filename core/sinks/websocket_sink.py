import asyncio
import queue
import time
import json

from fastapi import WebSocket

from core.sinks.game_sink import GameEventSink


class WebSocketSink(GameEventSink):
    """Serialises game events to JSON and broadcasts over a websocket."""

    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.websocket = websocket
        self.loop = loop
        self._disconnected = False
        self._input_queue: queue.Queue = queue.Queue()
        self._step_queue: queue.Queue = queue.Queue()

    def _send(self, payload: dict):
        if self._disconnected:
            return
        future = asyncio.run_coroutine_threadsafe(
            self.websocket.send_text(json.dumps(payload)),
            self.loop,
        )
        future.result(timeout=5)

    # -- Game lifecycle -------------------------------------------------------

    def on_game_intro(self, message: str):
        self._send({"type": "game_intro", "message": message})

    def on_game_over(self, winner_name: str):
        self._send({"type": "game_over", "winner": winner_name})

    # -- Phase lifecycle ------------------------------------------------------

    def on_phase_header(self, phase_number: int):
        self._send({"type": "phase_header", "phase_number": phase_number})

    def on_phase_intro(self, host_text: str, summary_text: str):
        self._send({"type": "phase_intro", "host_text": host_text, "summary_text": summary_text})

    def on_phase_rounds(self, rounds: list[str]):
        self._send({"type": "phase_rounds", "rounds": rounds})

    def on_phase_round_index(self, index: int):
        self._send({"type": "phase_round_index", "index": index})

    # -- Round lifecycle ------------------------------------------------------

    def on_round_start(self, round_number: int, scores: str):
        self._send({"type": "round_start", "round_number": round_number, "scores": scores})

    def on_round_summary(self, summary: str):
        self._send({"type": "round_summary", "summary": summary})

    def on_turn_header(self, turn_number: int):
        self._send({"type": "turn_header", "turn_number": turn_number})

    # -- Actions --------------------------------------------------------------

    def on_public_action(self, speaker, message: str, color: str = "", animate: bool = True):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({"type": "public_action", "speaker": speaker_name, "message": message, "animate": animate})
        

    def on_private_thought(self, speaker, message: str):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({"type": "private_thought", "speaker": speaker_name, "message": message})

    def on_inner_workings(self, speaker, inner_workings):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({
            "type": "inner_workings",
            "speaker": speaker_name,
            "data": {k: str(v) for k, v in inner_workings},
        })

    def on_warning(self, message: str):
        self._send({"type": "warning", "message": message})

    def system_private(self, message: str):
        self._send({"type": "system_private", "message": str(message)})

    def on_points_update(self, points: dict):
        self._send({"type": "points_update", "scores": points})

    def on_evictions_update(self, evicted_names: list[str]):
        self._send({"type": "evicted_update", "evicted_names": evicted_names})

    def on_private_conversation(self, entry) -> None:
        messages = [{"speaker": m["speaker"], "message": m["message"]} for m in entry.messages]
        self._send({"type": "private_conversation", "messages": messages})

    # -- Human input ----------------------------------------------------------

    def get_user_input_simple(self, field_name: str, description: str) -> str:
        self._send({"type": "input_request", "field": field_name, "description": description})
        result = self._input_queue.get()
        if self._disconnected:
            raise RuntimeError("Client disconnected")
        return result

    def get_user_input_multiple_choice(self, field_name, description, choices):
        self._send({"type": "input_request", "field": field_name, "description": description, "choices": choices})
        result = self._input_queue.get() #this will be None if its disconnected
        if self._disconnected:
            raise RuntimeError("Client disconnected")
        return result

    def await_continue(self):
        self._send({"type": "awaiting_next"})
        result = self._step_queue.get()
        if self._disconnected:
            raise RuntimeError("Client disconnected")
        return result

    def on_disconnect(self):
        self._disconnected = True
        self._input_queue.put(None)
        self._step_queue.put(None)

    def on_segment_titles(self, titles: list[str]):
        self._send({"type": "set_segments", "titles": titles})

    def on_feed_marker(self, label: str):
        self._send({"type": "feed_marker", "label": label})

    def on_widget_update(self, widget):
        self._send({"type": "widget_update", "widget": widget})

    def loading_string(self, message: str):
        self._send({"type": "loading", "message": message})

    def end_loading(self):
        self._send({"type": "loading_done"})

    def delay(self, delay: float = 0.0):
        pass
        #time.sleep(delay)

