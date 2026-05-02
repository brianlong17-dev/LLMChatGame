import asyncio
import json
import os
import threading

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.sinks.websocket_sink import WebSocketSink
from runtime_tests.demo_runner import DEMO_REGISTRY

load_dotenv()

app = FastAPI()

# Feature flags — set to True to enable before publishing
GAME_ENABLED = False
DEMO_ENABLED = True

_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
_active_games = 0
_active_games_lock = threading.Lock()
MAX_CONCURRENT_GAMES = 5

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
    audio_bytes = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB)")
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
# Flags endpoint
# ---------------------------------------------------------------------------

@app.get("/api/flags")
async def get_flags():
    return {"game_enabled": GAME_ENABLED, "demo_enabled": DEMO_ENABLED}

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
    global _active_games
    await websocket.accept()

    if not GAME_ENABLED:
        await websocket.send_text(json.dumps({"type": "error", "message": "Game is not available yet."}))
        await websocket.close()
        return

    loop = asyncio.get_event_loop()

    with _active_games_lock:
        if _active_games >= MAX_CONCURRENT_GAMES:
            await websocket.send_text(json.dumps({"type": "error", "message": f"Server is at capacity ({MAX_CONCURRENT_GAMES} active games). Try again soon."}))
            await websocket.close()
            return
        _active_games += 1

    sink = None
    try:
        # Wait for the "start" message from the client
        data = await websocket.receive_text()
        msg = json.loads(data)
        if msg.get("type") != "start":
            await websocket.send_text(json.dumps({"type": "error", "message": "Expected start message"}))
            return

        sink = WebSocketSink(websocket, loop)

        player_names = [str(n)[:30] for n in msg.get("names", [])[:12]]
        human_player_name = str(msg["human_name"])[:30] if msg.get("human_name") else None

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
                    sink._input_queue.put(str(msg.get("value", ""))[:5000])
                elif msg.get("type") == "next_turn":
                    sink._step_queue.put(True)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        if sink: sink.on_disconnect()
    finally:
        with _active_games_lock:
            _active_games -= 1



# ---------------------------------------------------------------------------
# Demos endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/demo")
async def demo_ws(websocket: WebSocket):
    global _active_games
    await websocket.accept()

    if not DEMO_ENABLED:
        await websocket.send_text(json.dumps({"type": "error", "message": "Demo is not available yet."}))
        await websocket.close()
        return

    loop = asyncio.get_event_loop()

    with _active_games_lock:
        if _active_games >= MAX_CONCURRENT_GAMES:
            await websocket.send_text(json.dumps({"type": "error", "message": f"Server is at capacity ({MAX_CONCURRENT_GAMES} active games). Try again soon."}))
            await websocket.close()
            return
        _active_games += 1

    sink = None
    try:
        data = await websocket.receive_text()
        msg = json.loads(data)
        demo_id = msg.get("demo_id")
        human_name = str(msg["human_name"])[:30] if msg.get("human_name") else None

        LOCKED_DEMOS = {"game_phase"}
        if demo_id in LOCKED_DEMOS:
            await websocket.send_text(json.dumps({"type": "error", "message": "This demo is not available yet."}))
            return

        runner = DEMO_REGISTRY.get(demo_id)
        if not runner:
            await websocket.send_text(json.dumps({"type": "error", "message": f"Unknown demo: {demo_id}"}))
            return

        sink = WebSocketSink(websocket, loop)
        def run_demo():
            try:
                runner(sink, human_name=human_name)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(json.dumps({"type": "error", "message": str(e)})),
                    loop,
                ).result(timeout=5)

        thread = threading.Thread(target=run_demo, daemon=True)
        thread.start()
        while thread.is_alive():
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                msg = json.loads(data)
                if msg.get("type") == "input_response":
                    sink._input_queue.put(str(msg.get("value", ""))[:5000])
                elif msg.get("type") == "next_turn":
                    sink._step_queue.put(True)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        if sink: sink.on_disconnect()
    finally:
        with _active_games_lock:
            _active_games -= 1
