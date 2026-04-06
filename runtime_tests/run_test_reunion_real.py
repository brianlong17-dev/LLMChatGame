"""
Test script for FinaleReunionRound using real game log data.
Loads agent state from a completed 11-player game (Amy March vs Lady Dianna finale).
"""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.bootstrap import create_engine, ConsoleGameEventSink
from core.phase_recipe import PhaseRecipe
from gameplay_management.reunion_round import FinaleReunionRound

if __name__ == "__main__":
    # ── 1. Load agent state from logs ──
    fixtures_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "reunion_agent_state_2.json")
    with open(fixtures_path) as f:
        agent_state = json.load(f)

    # ── 2. Bootstrap with the real character names ──
    all_names = list(agent_state.keys())
    sink = ConsoleGameEventSink()
    engine = create_engine(sink, names=all_names, allow_rename=False)
    engine.initialiseGameBoard()

    # ── 3. Build name->agent lookup ──
    agents = {a.name: a for a in engine.agents}

    # ── 4. Set scores (only finalists have non-zero scores at this point) ──
    engine.gameBoard.agent_scores["Amy March"] = 41
    engine.gameBoard.agent_scores["Lady Dianna"] = 48

    # ── 5. Eliminate dead agents in order (earliest eliminated first) ──
    elimination_order = [
        "Morty Smith",
        "Lady Macbeth",
        "HAL 9000",
        "Jo March",
        "Michael Jackson",
        "Avatar Aang", #Aang
        "Gollum",
        "Buffy Summers",
        "Benoit Blanc",
    ]

    for name in elimination_order:
        agent = agents[name]
        engine.eliminate_player(agent)
        engine.gameBoard.remove_agent_state(agent.name)

    # ── 6. Apply saved state to all agents ──
    for name, state in agent_state.items():
        agent = agents[name]
        agent.debug_log = False

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

    # ── 7. Run the reunion ──
    engine.gameBoard.new_phase()
    engine.gameBoard.newRound()

    phase = PhaseRecipe(rounds=[FinaleReunionRound])
    engine.phase_runner.run_phase(phase)
