import asyncio
import dataclasses
import queue
import random
import time
import json
import os
import uuid
import threading
from datetime import datetime, timezone

from fastapi import WebSocket

from core.sinks.game_sink import GameEventSink
from core import backend_config
from core.shared_helpers import INACTIVITY_TIMEOUT
INACTIVITY_MESSAGE = f"Session timed out due to inactivity ({INACTIVITY_TIMEOUT//60} minutes)"

_ONES = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _number_to_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] + (f"-{_ONES[ones].lower()}" if ones else "")
    return str(n)

class InactivityTimeout(Exception):
    def __init__(self):
        super().__init__("Session timed out due to inactivity")

def _prune_logs(log_dir: str, keep: int) -> None:
    logs = sorted(os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".jsonl"))
    for old in logs[:-keep]:
        os.remove(old)

class WebSocketSink(GameEventSink):
    """Serialises game events to JSON and broadcasts over a websocket."""

    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop, should_kick_idle=None):
        self.websocket = websocket
        self.loop = loop
        self._should_kick_idle = should_kick_idle or (lambda: False)
        self._disconnected = False
        self._input_queue: queue.Queue = queue.Queue()
        self._round_gate = threading.Event()
        self._round_gate.set()
        self.mobile_outputs: bool = False
        self.auto_run: bool = False
        self._public_action_count = 0
        self.log_file = None
        if backend_config.GAME_LOGGING_ENABLED:
            self._initialise_log_file()
            
    def _initialise_log_file(self):
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "gamelogs")
        os.makedirs(log_dir, exist_ok=True)
        _prune_logs(log_dir, keep=400)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:6]
        self.log_file = os.path.join(log_dir, f"game_{timestamp}_{suffix}.jsonl")

    def _record_payload(self, payload):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _send(self, payload: dict):
        
        if self._disconnected:
            return
        if self.log_file:
            self._record_payload(payload)
        future = asyncio.run_coroutine_threadsafe(
            self.websocket.send_text(json.dumps(payload)),
            self.loop,
        )
        future.result(timeout=5)

    # -- Game lifecycle -------------------------------------------------------

    def on_game_intro(self, message: str):
        self._send({"type": "game_intro", "message": message})

    def output_tutorial_message(self, message: str, hold: bool = True, next_level: str | None = None):
        self._public_action_count += 1
        self._send({"type": "public_action", "speaker": "HOST", "message": message,
                    "animate_as_player": False, "should_hold": False, "is_human": False,
                    "tutorial_message": True, "tutorial_hold": hold, "next_level": next_level,
                    "message_id": f"0-{self._public_action_count}"})

    def on_linebreak(self):
        self._send({"type": "linebreak"})

    def on_game_over(self, winner_names: list[str]):
        self._send({"type": "game_over", "winners": winner_names})

    # -- Phase lifecycle ------------------------------------------------------

    def on_phase_header(self, phase_number: int):
        self._send({"type": "phase_header", "phase_number": phase_number})

    def on_phase_intro(self, host_text: str, summary_text: str):
        #depreciate
        self._send({"type": "phase_intro", "host_text": host_text, "summary_text": summary_text})

    def on_phase_rounds(self, rounds: list[str]):
        self._send({"type": "phase_rounds", "rounds": rounds})

    def on_phase_round_index(self, index: int):
        self._send({"type": "phase_round_index", "index": index})

    # -- Round lifecycle ------------------------------------------------------

    def on_round_start(self, round_number: int, round_type: str, round_name: str, scores: str):
        self._send({"type": "round_start", "round_number": _number_to_words(round_number), "round_type": round_type, "round_name": round_name, "scores": scores})

    def on_round_summary(self, summary: str):
        self._send({"type": "round_summary", "summary": summary})

    # -- Actions --------------------------------------------------------------

    def on_public_action(self, speaker, message: str, color: str = "", animate_as_player: bool = True,
                         should_hold: bool = True, directed_to_name=None, is_reply: bool = False,
                         is_human: bool = False, pop_wrap=False, widget: dict | None = None):
        if directed_to_name:
            message = f"@{directed_to_name} - {message}"
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._public_action_count += 1
        event = {"type": "public_action", "speaker": speaker_name, "message": message,
                 "animate_as_player": animate_as_player, "should_hold": should_hold,
                 "is_human": is_human, "message_id": f"0-{self._public_action_count}"}
        if is_reply:
            event["child"] = True
        if pop_wrap:
            event["pop_wrap"] = True
        if widget is not None:
            event["widget"] = widget
        self._send(event)
        

    def on_private_thought(self, speaker, message: str):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({"type": "private_thought", "speaker": speaker_name, "message": message})

    def on_warning(self, message: str):
        self._send({"type": "warning", "message": message})

    def system_private(self, message: str, border_bottom: bool = False):
        self._send({"type": "system_private", "message": str(message), "border_bottom": border_bottom})
        
    def system_public(self, message: str, border_bottom: bool = False):
        self._send({"type": "system_public", "message": str(message), "border_bottom": border_bottom})

    def on_points_update(self, points: dict):
        self._send({"type": "points_update", "scores": points})

    def on_evictions_update(self, evicted_names: list[str]):
        self._send({"type": "evicted_update", "evicted_names": evicted_names})

    def on_private_conversation(self, message_block) -> None:
        participants = sorted(message_block.visibility_restriction) if message_block.visibility_restriction else []
        messages = [{"speaker": message_entry.speaker, "message": message_entry.public_output} for message_entry in message_block.message_entries]
        self._send({"type": "private_conversation", "participants": participants, "messages": messages})

    # -- Human input ----------------------------------------------------------

    def wait_for_continue_next_round(self):
        while not self._round_gate.wait(timeout=INACTIVITY_TIMEOUT):
            self._on_timeout()
        self._round_gate.clear()
        if self._disconnected:
            raise RuntimeError("Client disconnected")
        
    def set_round_gate_open(self):
        self._round_gate.set()
        
    def _request_continue_next_round(self):
        self._send({"type": "next_round_request"})
        
    def get_user_input_form(self, form):
        self._send({"type": "input_form_request", "form": dataclasses.asdict(form)})
        while True:
            try:
                values = self._input_queue.get(timeout=INACTIVITY_TIMEOUT)
                break
            except queue.Empty:
                self._on_timeout()
        if self._disconnected:
            raise RuntimeError("Client disconnected")
        return values

    def _on_timeout(self):
        if not self._should_kick_idle():
            return
        self.system_private(INACTIVITY_MESSAGE)
        raise InactivityTimeout()

    def on_disconnect(self):
        self._disconnected = True
        self._input_queue.put(None)
        self._round_gate.set()

    def on_cast(self, names: list[str]):
        self._send({"type": "cast", "names": names})

    def on_segment_titles(self, titles: list[str]):
        self._send({"type": "set_segments", "titles": titles})

    def on_feed_marker(self, label: str):
        self._send({"type": "feed_marker", "label": label})

    def on_widget_update(self, widget):
        self._send({"type": "widget_update", "widget": widget})

    def add_summary_commentary_for_phase(self, agent_name: str, commentary: str, phase_number: int):
        self._send({"type": "summary_commentary", "phase_id": phase_number, "speaker": agent_name, "message": commentary})

    def update_is_typing(self, typing_names: list[str]):
        if not typing_names:
            typing_string = None
        elif len(typing_names) == 1:
            typing_string = f"{typing_names[0]} is typing..."
        else:
            typing_string = f"{len(typing_names)} players are typing..."
        self._send({"type": "is_typing", "message": typing_string})

    def loading_string(self, message: str):
        self._send({"type": "loading", "message": message})

    def end_loading(self, message: str = None):
        self._send({"type": "loading_done", "message": message})

    def delay(self, delay: float = 0.0):
        if delay <= 0:
            return
        jittered = delay + random.uniform(0, 1)
        time.sleep(jittered) #the backend runs ahead and normal messages then shoot out.
        #would need a more complex design that front end delay, maybe a 1.5 between all public messages. 
        
        #self._send({"type": "delay", "ms": int(jittered * 1000)})

