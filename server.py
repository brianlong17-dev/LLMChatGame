import asyncio
import json
import threading
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.sinks.game_sink import GameEventSink

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# WebSocket Sink
# ---------------------------------------------------------------------------

class WebSocketSink(GameEventSink):
    """Serialises game events to JSON and broadcasts over a websocket."""

    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self.websocket = websocket
        self.loop = loop

    def _send(self, payload: dict):
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

    # -- Round lifecycle ------------------------------------------------------

    def on_round_start(self, round_number: int, scores: str):
        self._send({"type": "round_start", "round_number": round_number, "scores": scores})

    def on_round_summary(self, summary: str):
        self._send({"type": "round_summary", "summary": summary})

    def on_turn_header(self, turn_number: int):
        self._send({"type": "turn_header", "turn_number": turn_number})

    # -- Actions --------------------------------------------------------------

    def on_public_action(self, speaker, message: str, color: str = ""):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({"type": "public_action", "speaker": speaker_name, "message": message})

    def on_private_thought(self, speaker, message: str):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({"type": "private_thought", "speaker": speaker_name, "message": message})

    def on_inner_workings(self, speaker, inner_workings, override: bool = False):
        if override:
            speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
            self._send({
                "type": "inner_workings",
                "speaker": speaker_name,
                "data": {k: str(v) for k, v in inner_workings},
            })

    def system_private(self, speaker, message: str):
        self._send({"type": "system_private", "message": str(message)})

    def on_points_update(self, points: dict):
        self._send({"type": "points_update", "scores": points})
        
    def on_evictions_update(self, evicted_names: list[str]):
        self._send({"type": "evicted_update", "evicted_names": evicted_names})

    # -- Human input (not supported in web mode yet) --------------------------

    def get_user_input_simple(self, field_name: str, description: str) -> str:
        raise RuntimeError("Human input not yet supported in web mode")

    def get_user_input_multiple_choice(self, field_name, description, choices):
        raise RuntimeError("Human input not yet supported in web mode")

    def delay(self, delay: float = 0.0):
        import time
        time.sleep(delay)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/game")
async def game_ws(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    try:
        # Wait for the "start" message from the client
        data = await websocket.receive_text()
        msg = json.loads(data)
        if msg.get("type") != "start":
            await websocket.send_text(json.dumps({"type": "error", "message": "Expected start message"}))
            return

        sink = WebSocketSink(websocket, loop)

        def run_game():
            try:
                from core.bootstrap import create_engine
                engine = create_engine(game_sink_class=lambda: sink)
                engine.run(number_of_players=3, generic_players=True, human_player=False)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({"type": "error", "message": str(e)})),
                    loop,
                ).result(timeout=5)

        thread = threading.Thread(target=run_game, daemon=True)
        thread.start()

        # Keep the connection alive until the game thread finishes or client disconnects
        while thread.is_alive():
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass