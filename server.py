import asyncio
import json
import os
import threading
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.sinks.websocket_sink import WebSocketSink
from runtime_tests.demo_runner import DEMO_REGISTRY
from core.api_client import api_client
from core.levels.level_registry import phase_factory_for_id

load_dotenv()

app = FastAPI()

# Feature flags — set to True to enable before publishing
GAME_ENABLED = True
DEMO_ENABLED = True

_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
_active_games = 0
_active_games_lock = threading.Lock()
MAX_CONCURRENT_GAMES = 5

_limit_lock = threading.Lock()
_games_today = 0
_limit_date = date.today()
DAILY_CAP = 20

def check_and_increment_global_limit() -> bool:
    global _games_today, _limit_date
    with _limit_lock:
        today = date.today()
        if today != _limit_date:
            _games_today = 0
            _limit_date = today
        if _games_today >= DAILY_CAP:
            return False
        _games_today += 1
        return True
    
@app.get("/api/status")
async def status():
    return {
        "games_today": _games_today,
        "cap": DAILY_CAP,
        "date": _limit_date.isoformat(),
        "remaining": max(0, DAILY_CAP - _games_today)
    }
    

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
async def transcribe(audio: UploadFile = File(...), names: str = Form("")):
    from fastapi import HTTPException
    MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
    audio_bytes = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB)")
    hints = json.loads(names) if names else None
    text = api_client.transcribe(audio_bytes, audio.content_type or "audio/webm", hints=hints)
    return {"text": text}

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
# Levels endpoint
# ---------------------------------------------------------------------------

@app.get("/api/levels")
async def get_levels():
    from core.levels import AVAILABLE_LEVELS
    return {
        "levels": [
            {
                "id": level.id,
                "name": level.name,
                "description": level.description,
                "min_players": level.min_players,
                "max_players": level.max_players,
                "locked": level.locked,
            }
            for level in AVAILABLE_LEVELS
        ]
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

    if not check_and_increment_global_limit():
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Daily game limit reached. Come back tomorrow."
        }))
        await websocket.close()
        return
    
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

        level_id = msg.get("levelId")
        
        
        
        phase_factory = phase_factory_for_id(level_id)

        def run_game():
            try:
                from core.bootstrap import create_engine
                if player_names:
                    engine = create_engine(sink, names=player_names, phase_factory=phase_factory)
                else:
                    engine = create_engine(sink, number_of_players=7, generic_players=False, phase_factory=phase_factory)
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
    
    
    if not check_and_increment_global_limit():
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Daily game limit reached. Come back tomorrow."
        }))
        await websocket.close()
        return
    
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

        LOCKED_DEMOS = {} #"game_phase"}
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
