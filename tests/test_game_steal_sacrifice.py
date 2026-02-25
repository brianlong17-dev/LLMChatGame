import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest


@pytest.fixture
def game_targeted_choice_module(monkeypatch):
    if "pydantic" not in sys.modules:
        fake = types.ModuleType("pydantic")

        class _BaseModel:
            pass

        def _field(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

        def _create_model(name, **fields):
            return type(name, (), {"__fields__": fields})

        def _identity_decorator(*args, **kwargs):
            def _inner(fn):
                return fn

            return _inner

        fake.BaseModel = _BaseModel
        fake.Field = _field
        fake.create_model = _create_model
        fake.field_validator = _identity_decorator
        fake.validator = _identity_decorator
        monkeypatch.setitem(sys.modules, "pydantic", fake)

    return importlib.import_module("gameplay_management.game_targeted_choice")


@pytest.fixture
def build_game(game_targeted_choice_module):
    def _build(players, scores):
        game_board = MagicMock()
        game_board.agent_names = [p.name for p in players]
        game_board.agent_scores = dict(scores)

        simulation = SimpleNamespace(agents=players)
        game = game_targeted_choice_module.GameTargetedChoice(game_board, simulation)
        game._shuffled_agents = MagicMock(return_value=players)
        game.publicPrivateResponse = MagicMock()
        game.respond_to = MagicMock()

        return game, game_board

    return _build


def _decision(action, points_to_spend=None):
    payload = {
        "action": action,
        "public_response": "pub",
        "private_thoughts": "priv",
    }
    if points_to_spend is not None:
        payload["points_to_spend"] = points_to_spend
    return SimpleNamespace(**payload)

def test_run_game_steal_standard_workflow_takes_full_prompt_points(
    build_game, game_targeted_choice_module, monkeypatch
):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    game, board = build_game([alice, bob], {"Alice": 10, "Bob": 10})

    monkeypatch.setattr(game_targeted_choice_module.GamePromptLibrary, "targeted_games_points", 4)

    alice.take_turn_standard.return_value = _decision("Bob")
    bob.take_turn_standard.return_value = _decision("Alice")

    game.respond_to.side_effect = [_decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_steal()

    board.append_agent_points.assert_has_calls(
        [
            call("Alice", 4),
            call("Bob", -4),
            call("Bob", 4),
            call("Alice", -4),
        ],
        any_order=False,
    )

    assert "steal 4 points" in alice.take_turn_standard.call_args.args[0]
    assert "steal 4 points" in bob.take_turn_standard.call_args.args[0]
    assert game.respond_to.call_args_list[0].args[0] is bob
    assert game.respond_to.call_args_list[1].args[0] is alice


def test_run_game_steal_handles_partial_and_zero_point_steals(build_game, game_targeted_choice_module):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    game, board = build_game([alice, bob], {"Alice": 0, "Bob": 2})

    # Alice steals from Bob (partial: only 2 available). Bob steals from Alice (0 available).
    alice.take_turn_standard.return_value = _decision("Bob")
    bob.take_turn_standard.return_value = _decision("Alice")

    game.respond_to.side_effect = [_decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_steal()

    board.append_agent_points.assert_has_calls(
        [
            call("Alice", 2),
            call("Bob", -2),
            call("Bob", 0),
            call("Alice", 0),
        ],
        any_order=False,
    )

    # First reaction should be from victim Bob (successful steal). Second from Bob (failed steal reacts self).
    assert game.respond_to.call_args_list[0].args[0] is bob
    assert "gains 2 points" in game.respond_to.call_args_list[0].args[1]
    assert game.respond_to.call_args_list[1].args[0] is bob
    assert "empty pockets" in game.respond_to.call_args_list[1].args[1]

def test_run_game_sacrifice_malformed_target(build_game, game_targeted_choice_module):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    game, board = build_game([alice, bob], {"Alice": 3, "Bob": 10})

    # Alice spends 2 => Bob loses 4. Bob uses an invalid target and should no-op.
    alice.take_turn_standard.return_value = _decision("Bob", points_to_spend=2)
    bob.take_turn_standard.return_value = _decision("XXX", points_to_spend=2)

    game.respond_to.side_effect = [_decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_sacrifice_points()

    board.append_agent_points.assert_has_calls(
        [
            call("Bob", -4)
        ],
        any_order=False,
    )

    # Attack result is reacted to by target Bob; pass result reacted to by actor Bob.
    assert game.respond_to.call_args_list[0].args[0] is bob
    assert "sacrifices 2" in game.respond_to.call_args_list[0].args[1]
    assert game.respond_to.call_args_list[1].args[0] is bob
    assert "invalid target" in game.respond_to.call_args_list[1].args[1]


def test_run_game_sacrifice_invalid_target_with_positive_spend_is_noop(build_game, game_targeted_choice_module):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    game, board = build_game([alice, bob], {"Alice": 7, "Bob": 10})

    alice.take_turn_standard.return_value = _decision("XXX", points_to_spend=3)
    bob.take_turn_standard.return_value = _decision("Pass", points_to_spend=0)

    game.respond_to.side_effect = [_decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_sacrifice_points()

    board.append_agent_points.assert_not_called()
    assert game.respond_to.call_args_list[0].args[0] is alice
    assert "invalid target" in game.respond_to.call_args_list[0].args[1]
    assert game.respond_to.call_args_list[1].args[0] is bob
    assert "passes" in game.respond_to.call_args_list[1].args[1]
    
    
def test_run_game_sacrifice_clamps_spend_and_handles_pass(build_game, game_targeted_choice_module):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    game, board = build_game([alice, bob], {"Alice": 3, "Bob": 10})

    # Alice overspends: clamped to 3 => Bob loses 6. Bob passes.
    alice.take_turn_standard.return_value = _decision("Bob", points_to_spend=9)
    bob.take_turn_standard.return_value = _decision("Pass", points_to_spend=0)

    game.respond_to.side_effect = [_decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_sacrifice_points()

    board.append_agent_points.assert_has_calls(
        [
            call("Alice", -3),
            call("Bob", -6),
        ],
        any_order=False,
    )

    # Attack result is reacted to by target Bob; pass result reacted to by actor Bob.
    assert game.respond_to.call_args_list[0].args[0] is bob
    assert "sacrifices 3" in game.respond_to.call_args_list[0].args[1]
    assert game.respond_to.call_args_list[1].args[0] is bob
    assert "passes" in game.respond_to.call_args_list[1].args[1]

def test_run_game_sacrifice_negative_points(build_game, game_targeted_choice_module):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    cara = MagicMock(); cara.name = "Cara"
    dan = MagicMock(); dan.name = "Dan"
    game, board = build_game(
        [alice, bob, cara, dan],
        {"Alice": 5, "Bob": 5, "Cara": 5})
    # Negative spend should be treated as a pass even with a valid target.
    alice.take_turn_standard.return_value = _decision("Bob", points_to_spend=-3)
    bob.take_turn_standard.return_value = _decision("Pass", points_to_spend=0)
    cara.take_turn_standard.return_value = _decision("Pass", points_to_spend=0)
    dan.take_turn_standard.return_value = _decision("Pass", points_to_spend=0)

    game.respond_to.side_effect = [_decision(""), _decision(""), _decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_sacrifice_points()

    board.append_agent_points.assert_not_called()
    assert "passes" in game.respond_to.call_args_list[0].args[1]
        

def test_run_game_sacrifice_edge_cases(build_game, game_targeted_choice_module):
    alice = MagicMock(); alice.name = "Alice"
    bob = MagicMock(); bob.name = "Bob"
    cara = MagicMock(); cara.name = "Cara"
    dan = MagicMock(); dan.name = "Dan"
    game, board = build_game(
        [alice, bob, cara, dan],
        {"Alice": 3, "Bob": 10, "Cara": 5, "Dan": 7, "Effie": 5, "Fred": 5, "Greg": 5},
    )

    # 1) Overspend is clamped to available score.
    alice.take_turn_standard.return_value = _decision("Bob", points_to_spend=999)
    # 2) Negative spend is treated as pass.
    bob.take_turn_standard.return_value = _decision("Cara", points_to_spend=-2)
    # 3) Explicit pass even with available points.
    cara.take_turn_standard.return_value = _decision("Pass", points_to_spend=4)
    # 4) Malformed pass name with zero spend still resolves as pass.
    dan.take_turn_standard.return_value = _decision("Pass???", points_to_spend=0)

    game.respond_to.side_effect = [_decision(""), _decision(""), _decision(""), _decision("")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_sacrifice_points()

    board.append_agent_points.assert_has_calls(
        [
            call("Alice", -3),
            call("Bob", -6),
        ],
        any_order=False,
    )
    assert board.append_agent_points.call_count == 2
    #assert board.agent_scores["Bob"] == 4

    assert game.respond_to.call_args_list[0].args[0] is bob
    assert "sacrifices 3" in game.respond_to.call_args_list[0].args[1]
    assert game.respond_to.call_args_list[1].args[0] is bob
    assert "passes" in game.respond_to.call_args_list[1].args[1]
    assert game.respond_to.call_args_list[2].args[0] is cara
    assert "passes" in game.respond_to.call_args_list[2].args[1]
    assert game.respond_to.call_args_list[3].args[0] is dan
    assert "passes" in game.respond_to.call_args_list[3].args[1]
