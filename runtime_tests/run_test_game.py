"""
Reusable game test sandbox.
Loads 11 real characters from phase-1 state, sets up scores, then runs a game.
Swap the game class at the bottom to test different games.
"""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")) 
from core.bootstrap import create_engine, ConsoleGameEventSink
from core.api_client import api_client
from core.phase_recipe import PhaseRecipe
from agents.human_player import Human
from runtime_tests.hardcoded_cast import build_hardcoded_debaters
from gameplay_management.game_cycle.game_circle import GameCircle
from gameplay_management.games.game_guess import GameGuess
from gameplay_management.game_cycle.game_mob import GameMob
from gameplay_management.game_cycle.game_knives import GameKnives
from gameplay_management.eliminations.voting_bottom_two import VoteBottomTwo

# from gameplay_management.games.game_knives import GameKnives

if __name__ == "__main__":
    # ── 1. Load agent state ──
    fixtures_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "game_agent_state.json")
    with open(fixtures_path) as f:
        agent_state = json.load(f)

    # ── 2. Bootstrap ──
    all_names = list(agent_state.keys())
    sink = ConsoleGameEventSink()
    hardcoded_agents = build_hardcoded_debaters(all_names)
    engine = create_engine(sink, agents=hardcoded_agents, allow_rename=False)
    add_human = False
    if add_human:
        human = Human('Brian')
        engine.agents.append(human)
    engine.initialiseGameBoard()

    # ── 3. Name -> agent lookup ──
    agents = {a.name: a for a in engine.agents}
    # ── 4. Scores from phase 1 ──
    scores = {
        "Aang":      12,
        "Michael Jackson":  10,
        "HAL 9000":         9,
        "Jo March":         12,
        "Lady Macbeth":     11,
        "Lady Diana":      13,
        "Morty Smith":      2,
        "Amy March":        12,
        "Benoit Blanc":     11,
        "Gollum":           9,
        "Buffy Summers":    10,
    }
    for name, score in scores.items():
        engine.gameBoard.agent_scores[name] = score
        if add_human:
             engine.gameBoard.agent_scores[human.name] = 9

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
    circle = True
    if circle:
        engine.gameplay_config.use_double_shots = True
        engine.gameplay_config.cycle_use_optional_response = True
        engine.gameplay_config.cycle_use_context_compression = True
        
        
    engine.gameBoard.new_phase()
    engine.gameBoard.newRound()
    rounds = 0
    #while len(engine.agents) > 2:
    while rounds < 1:
        rounds += 1
        phase = PhaseRecipe(rounds=[GameCircle, VoteBottomTwo])
        engine.phase_runner.run_phase(phase)
    api_client.print_summary()
