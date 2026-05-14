"""
Demo runner functions — callable versions of the runtime test scripts.
Each function accepts a sink (any GameEventSink) and an optional human_name.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")


def _load_fixture(filename: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, filename)) as f:
        return json.load(f)


def _apply_agent_state(agents: dict, agent_state: dict):
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
            agent.position_assessment = state["math_assessment"]

        agent.life_lessons.clear()
        for lesson in state["life_lessons"]:
            agent.life_lessons.append(lesson)

        for phase_str, text in state["summaries_detailed"].items():
            agent.phase_summaries_detailed[int(phase_str)] = text
        for phase_str, text in state["summaries_brief"].items():
            agent.phase_summaries_brief[int(phase_str)] = text


def _run_reunion(sink, fixture_filename: str, finalist_scores: dict, elimination_order: list, human_name: str = None, phase_number = None):
    from core.bootstrap import create_engine
    from core.levels.phase_recipe import PhaseRecipe
    from gameplay_management.eliminations.reunion_round import FinaleReunionRound
    from agents.human_player import Human
    from core.bootstrap import create_agent

    agent_state = _load_fixture(fixture_filename)
    all_names = list(agent_state.keys())
    agents = [create_agent(name) for name in all_names]

    engine = create_engine(sink, agents=agents, allow_rename=False)
    if phase_number:
        engine.gameBoard.phase_number = 11

    if human_name:
        human = Human(human_name)
        agent_to_replace = next((a for a in engine.agents if a.name == human_name), None)
        if agent_to_replace:
            engine.agents.remove(agent_to_replace)
            engine.agents.append(human)
        else:
            human.game_over = True
            engine.dead_agents.append(human)

    engine.initialiseGameBoard()
    agents = {a.name: a for a in engine.agents}

    for name, score in finalist_scores.items():
        engine.gameBoard.agent_scores[name] = score

    

    for name in elimination_order:
        agent = agents[name]
        engine.eliminate_player(agent)
        engine.gameBoard.remove_agent_state(agent.name)

    _apply_agent_state(agents, agent_state)

    phase = PhaseRecipe(rounds=[FinaleReunionRound])
    engine.phase_runner.run_phase(phase)


def run_demo_reunion_3(sink, human_name: str = None):
    """Reunion Finale — Game 3: Avatar Aang vs Morty Smith (tied 39–39)."""
    _run_reunion(
        sink,
        fixture_filename="reunion_agent_state_3.json",
        finalist_scores={"Avatar Aang": 39, "Morty Smith": 39},
        elimination_order=[
            "HAL 9000", "Michael Jackson", "Amy March", "Benoit Blanc",
            "Buffy Summers", "Gollum", "Lady Macbeth", "Jo March", "Lady Dianna",
        ],
        human_name=human_name,
        phase_number = 11
    )


def run_demo_reunion_2(sink, human_name: str = None):
    """Reunion Finale — Game 2: Amy March vs Lady Dianna (41 vs 48)."""
    _run_reunion(
        sink,
        fixture_filename="reunion_agent_state_2.json",
        finalist_scores={"Amy March": 41, "Lady Dianna": 48},
        elimination_order=[
            "Morty Smith", "Lady Macbeth", "HAL 9000", "Jo March",
            "Michael Jackson", "Avatar Aang", "Gollum", "Buffy Summers", "Benoit Blanc",
        ],
        human_name=human_name,
    )


def run_demo_game(sink, human_name: str = None):
    """Game Phase: 11 real players, mid-game Knives + Vote round."""
    from core.bootstrap import create_engine
    from core.levels.phase_recipe import PhaseRecipe
    from gameplay_management.game_cycle.game_knives import GameKnives
    from gameplay_management.game_targeted.game_targeted_give import GameTargetedChoiceGive
    from gameplay_management.eliminations.voting_bottom_two import VoteBottomTwo
    from agents.human_player import Human

    agent_state = _load_fixture("game_agent_state.json")
    all_names = list(agent_state.keys())

    engine = create_engine(sink, names=all_names, allow_rename=False)

    if human_name:
        human = Human(human_name)
        engine.agents.append(human)

    engine.initialiseGameBoard()
    agents = {a.name: a for a in engine.agents}

    scores = {
        "Aang": 12, "Michael Jackson": 10, "HAL 9000": 9,
        "Jo March": 12, "Lady Macbeth": 11, "Lady Diana": 13,
        "Morty Smith": 2, "Amy March": 12, "Benoit Blanc": 11,
        "Gollum": 9, "Buffy Summers": 10,
    }
    for name, score in scores.items():
        engine.gameBoard.agent_scores[name] = score

    if human_name:
        engine.gameBoard.agent_scores[human_name] = 9

    _apply_agent_state(agents, agent_state)

    round_count = 0
    #while len(engine.agents) > 2:
    while round_count < 1:
        round_count += 1
        phase = PhaseRecipe(rounds=[GameTargetedChoiceGive, VoteBottomTwo])
        engine.phase_runner.run_phase(phase)


DEMO_REGISTRY = {
    "reunion_3": run_demo_reunion_3,
    "reunion_2": run_demo_reunion_2,
    "game_phase": run_demo_game,
}
