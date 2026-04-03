import asyncio
import json
import queue
import threading

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
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
        self._input_queue: queue.Queue = queue.Queue()

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

    def on_public_action(self, speaker, message: str, color: str = ""):
        speaker_name = speaker.name if hasattr(speaker, "name") else str(speaker)
        self._send({"type": "public_action", "speaker": speaker_name, "message": message})

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
        return self._input_queue.get()

    def get_user_input_multiple_choice(self, field_name, description, choices):
        self._send({"type": "input_request", "field": field_name, "description": description, "choices": choices})
        return self._input_queue.get()

    def delay(self, delay: float = 0.0):
        import time
        time.sleep(delay)


# ---------------------------------------------------------------------------
# Transcribe endpoint
# ---------------------------------------------------------------------------

@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    import os
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types
    load_dotenv()
    audio_bytes = await audio.read()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=audio.content_type or "audio/webm"),
            "Transcribe this audio exactly. Return only the spoken words, nothing else.",
        ],
    )
    return {"text": response.text.strip()}

# ---------------------------------------------------------------------------
# Characters endpoint
# ---------------------------------------------------------------------------

@app.get("/api/characters")
async def get_characters():
    from agents.character_generation.character_lister import CharacterLister
    lister = CharacterLister()
    return {
        "tabs": {
            "Classics": lister.goats,
            "Generics": lister.generics,
            "Schemers": lister.schemers,
            "Regulars": lister.regulars,
            "Little Women" : lister.marches,
            "Hot Heads": lister.agros,
            "Logicos": lister.logicos,
            "All": list(dict.fromkeys(lister.full_characters)),  # dedupe
        }
    }

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

        player_names = msg.get("names", [])
        human_player_name = msg.get("human_name", None)

        def run_game():
            try:
                from core.bootstrap import create_engine
                if player_names:
                    engine = create_engine(sink, names=player_names)
                else:
                    engine = create_engine(sink, number_of_players=7, generic_players=False)
                engine.run(human_player_name=human_player_name)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({"type": "error", "message": str(e)})),
                    loop,
                ).result(timeout=5)

        thread = threading.Thread(target=run_game, daemon=True)
        thread.start()

        # Keep the connection alive, routing input responses to the sink
        while thread.is_alive():
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                msg = json.loads(data)
                if msg.get("type") == "input_response":
                    sink._input_queue.put(msg.get("value", ""))
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        pass