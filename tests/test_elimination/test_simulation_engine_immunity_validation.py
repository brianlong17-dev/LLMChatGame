from types import SimpleNamespace

import pytest

from core.simulation_engine import SimulationEngine


class _BoardStub:
    def __init__(self):
        self.host_messages = []
        self.system_messages = []
        self.public_messages = []

    def host_broadcast(self, message):
        self.host_messages.append(message)

    def system_broadcast(self, message):
        self.system_messages.append(message)

    def broadcast_public_action(self, speaker, message, color=""):
        self.public_messages.append((speaker, message, color))


def _make_engine(agent_names):
    engine = SimulationEngine.__new__(SimulationEngine)
    engine.phase_number = 1
    engine.agents = [SimpleNamespace(name=name) for name in agent_names]
    engine.gameBoard = _BoardStub()
    engine.game_manager = SimpleNamespace(run_discussion_round=lambda: None)
    engine.printPhaseHeader = lambda: None
    engine.trigger_new_round = lambda: None
    return engine


def _make_recipe(immunity_types, vote_exec):
    return SimpleNamespace(
        pre_game_discussion_rounds=0,
        mini_game=None,
        pre_vote_discussion_rounds=0,
        vote_type=SimpleNamespace(
            display_name="Vote",
            rules_description="rules",
            execute_game=vote_exec,
        ),
        post_vote_discussion_rounds=0,
        immunity_types=immunity_types,
        phase_intro_string=lambda _phase, _count: ("intro", "summary"),
    )


def test_run_phase_raises_if_immunity_returns_non_list():
    engine = _make_engine(["Alice", "Bob"])
    recipe = _make_recipe(
        [
            SimpleNamespace(
                display_name="Bad immunity",
                execute_game=lambda _manager: "Alice",
            )
        ],
        vote_exec=lambda _manager, immunity_players=None: None,
    )

    with pytest.raises(TypeError, match="must return list\\[str\\]"):
        SimulationEngine.runPhase(engine, recipe)


def test_run_phase_raises_if_immunity_returns_non_string_entries():
    engine = _make_engine(["Alice", "Bob"])
    recipe = _make_recipe(
        [
            SimpleNamespace(
                display_name="Bad immunity",
                execute_game=lambda _manager: ["Alice", 123],
            )
        ],
        vote_exec=lambda _manager, immunity_players=None: None,
    )

    with pytest.raises(TypeError, match="must return list\\[str\\]"):
        SimulationEngine.runPhase(engine, recipe)


def test_run_phase_raises_if_immunity_returns_unknown_player_name():
    engine = _make_engine(["Alice", "Bob"])
    recipe = _make_recipe(
        [
            SimpleNamespace(
                display_name="Bad immunity",
                execute_game=lambda _manager: ["Ghost"],
            )
        ],
        vote_exec=lambda _manager, immunity_players=None: None,
    )

    with pytest.raises(ValueError, match="unknown player name"):
        SimulationEngine.runPhase(engine, recipe)


def test_run_phase_dedupes_immunity_names_before_vote_dispatch():
    engine = _make_engine(["Alice", "Bob", "Cara"])
    seen = []
    recipe = _make_recipe(
        [
            SimpleNamespace(
                display_name="Immunity A",
                execute_game=lambda _manager: ["Alice", "Bob"],
            ),
            SimpleNamespace(
                display_name="Immunity B",
                execute_game=lambda _manager: ["Bob", "Alice", "Alice"],
            ),
        ],
        vote_exec=lambda _manager, immunity_players=None: seen.append(list(immunity_players)),
    )

    SimulationEngine.runPhase(engine, recipe)

    assert seen == [["Alice", "Bob"]]

