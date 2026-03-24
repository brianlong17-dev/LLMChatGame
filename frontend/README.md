# Game Frontend

## Setup

### 1. Install backend dependencies
Make sure `fastapi` and `websockets` are installed in your project env:
```
pip install fastapi "uvicorn[standard]" websockets
```

### 2. Run the backend
From the **root of your repo**:
```
uvicorn server:app --reload --port 8000
```

### 3. Run the frontend
```
cd frontend
npm install
npm run dev
```
Then open http://localhost:5173

## File locations
- `server.py` — FastAPI websocket server, lives at repo root
- `frontend/` — Vite React app

## Event types
| type | goes to |
|------|---------|
| `public_action` | chat feed |
| `private_thought` | collapsible in feed |
| `system_private` | dimmed in feed (toggle-able) |
| `round_summary` | collapsible in feed |
| `phase_header` | section divider in feed |
| `round_start` | round marker in feed |
| `points_update` | scoreboard sidebar (live) |
| `game_over` | feed + disables start button |
