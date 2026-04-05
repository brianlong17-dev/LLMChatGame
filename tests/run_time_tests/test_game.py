"""
Reusable game test sandbox.
Loads 11 real characters from phase-1 state, sets up scores, then runs a game.
Swap the game class at the bottom to test different games.
"""
import json
import os
from core.bootstrap import create_engine, ConsoleGameEventSink
from core.phase_recipe import PhaseRecipe
from gameplay_management.games.game_circle import GameCircle
# from gameplay_management.games.game_knives import GameKnives

# ── 1. Load agent state ──
fixtures_path = os.path.join(os.path.dirname(__file__), "tests", "fixtures", "game_agent_state.json")
with open(fixtures_path) as f:
    agent_state = json.load(f)

# ── 2. Bootstrap ──
all_names = list(agent_state.keys())
sink = ConsoleGameEventSink()
engine = create_engine(sink, names=all_names)
engine.initialiseGameBoard()

# ── 3. Name -> agent lookup ──
agents = {a.name: a for a in engine.agents}
for name in agents:
    print(name)
# ── 4. Scores from phase 1 ──
scores = {
    "Avatar Aang":      12,
    "Michael Jackson":  10,
    "HAL 9000":         12,
    "Jo March":         16,
    "Lady Macbeth":     3,
    "Lady Dianna":      8,
    "Morty Smith":      2,
    "Amy March":        10,
    "Benoit Blanc":     13,
    "Gollum":           0,
    "Buffy Summers":    0,
}
for name, score in scores.items():
    engine.gameBoard.agent_scores[name] = score

# ── 5. Apply saved state ──
for name, state in agent_state.items():
    agent = agents[name]
    agent.debug_log = True

    if state["persona"]:
        agent.persona = state["persona"]
    if state["speaking_style"]:
        agent.speaking_style = state["speaking_style"]
    if state["strategy"]:
        agent.game_strategy = state["strategy"]
    if state["math_assessment"]:
        agent.mathematical_assessment = state["math_assessment"]

    agent.life_lessons.clear()
    for lesson in state["life_lessons"]:
        agent.life_lessons.append(lesson)

    for phase_str, text in state["summaries_detailed"].items():
        agent.phase_summaries_detailed[int(phase_str)] = text
    for phase_str, text in state["summaries_brief"].items():
        agent.phase_summaries_brief[int(phase_str)] = text

# ── 6. Run the game ──
engine.gameBoard.new_phase()
engine.gameBoard.newRound()

phase = PhaseRecipe(rounds=[GameCircle])
engine.phase_runner.run_phase(phase)
