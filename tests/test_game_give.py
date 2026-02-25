import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest


@pytest.fixture
def game_targeted_choice_module(monkeypatch):
    """Import module with a tiny pydantic stub when pydantic is unavailable."""
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

    module = importlib.import_module("gameplay_management.game_targeted_choice")
    return module


@pytest.fixture
def build_game(game_targeted_choice_module):
    def _build_game(players):
        game_board = MagicMock()
        game_board.agent_names = [p.name for p in players]
        game_board.agent_scores = {p.name: 0 for p in players}

        simulation = SimpleNamespace(agents=players)
        game = game_targeted_choice_module.GameTargetedChoice(game_board, simulation)

        game._shuffled_agents = MagicMock(return_value=players)
        game.publicPrivateResponse = MagicMock()
        game.respond_to = MagicMock()

        return game, game_board

    return _build_game


def _decision(action, public="pub", private="priv"):
    return SimpleNamespace(action=action, public_response=public, private_thoughts=private)


def test_give_awards_points_to_selected_target_for_each_turn(build_game, game_targeted_choice_module):
    a = MagicMock(); a.name = "Alice"
    b = MagicMock(); b.name = "Bob"
    game, board = build_game([a, b])

    a.take_turn_standard.return_value = _decision("Bob")
    b.take_turn_standard.return_value = _decision("Alice")

    game.respond_to.side_effect = [_decision("", "r1", "t1"), _decision("", "r2", "t2")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_give()

    board.append_agent_points.assert_has_calls([call("Bob", 3), call("Alice", 3)], any_order=False)
    game.respond_to.assert_has_calls([
        #is it ok to check for hard coded strings? are these defined in the prompt factory? should we move them?
        call(b, "Yay! Alice chooses Bob! They receive 3 points."),
        call(a, "Yay! Bob chooses Alice! They receive 3 points."),
    ])


def test_give_invalid_self_choice_gets_no_points_and_self_reacts(build_game, game_targeted_choice_module):
    a = MagicMock(); a.name = "Alice"
    b = MagicMock(); b.name = "Bob"
    game, board = build_game([a, b])

    a.take_turn_standard.return_value = _decision("Alice")
    b.take_turn_standard.return_value = _decision("Alice")

    game.respond_to.side_effect = [_decision("", "r1", "t1"), _decision("", "r2", "t2")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_give()

    # Only Bob's valid give should score.
    board.append_agent_points.assert_called_once_with("Alice", 3)

    first_reaction_player = game.respond_to.call_args_list[0].args[0]
    assert first_reaction_player is a
    #dito for invalid choice
    assert "invalid choice" in game.respond_to.call_args_list[0].args[1]


def test_give_unknown_name_is_invalid_and_scores_nothing(build_game, game_targeted_choice_module):
    a = MagicMock(); a.name = "Alice"
    b = MagicMock(); b.name = "Bob"
    game, board = build_game([a, b])

    a.take_turn_standard.return_value = _decision("NotAPlayer")
    b.take_turn_standard.return_value = _decision("NotAPlayer")

    game.respond_to.side_effect = [_decision("", "r1", "t1"), _decision("", "r2", "t2")]
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_give()

    board.append_agent_points.assert_not_called()
    assert game.respond_to.call_count == 2
    assert all("invalid choice" in c.args[1] for c in game.respond_to.call_args_list)


def test_give_model_choices_exclude_current_player(build_game, game_targeted_choice_module):
    a = MagicMock(); a.name = "Alice"
    b = MagicMock(); b.name = "Bob"
    c = MagicMock(); c.name = "Cara"
    game, _board = build_game([a, b, c])

    a.take_turn_standard.return_value = _decision("Bob")
    b.take_turn_standard.return_value = _decision("Cara")
    c.take_turn_standard.return_value = _decision("Alice")

    game.respond_to.side_effect = [_decision("", "r1", "t1"), _decision("", "r2", "t2"), _decision("", "r3", "t3")]
    game._choose_name_field = MagicMock(return_value={"action": (str, "field")})
    game_targeted_choice_module.DynamicModelFactory.create_model_ = MagicMock(return_value=object())

    game.run_game_give()

    expected_lists = [
        ["Bob", "Cara"],
        ["Alice", "Cara"],
        ["Alice", "Bob"],
    ]
    observed_lists = [c.args[0] for c in game._choose_name_field.call_args_list]
    assert observed_lists == expected_lists


def test_run_targeted_round_supports_target_name_when_action_missing(build_game):
    a = MagicMock(); a.name = "Alice"
    b = MagicMock(); b.name = "Bob"
    game, board = build_game([a, b])

    a.take_turn_standard.return_value = SimpleNamespace(target_name="Bob", public_response="pub", private_thoughts="priv")
    b.take_turn_standard.return_value = SimpleNamespace(target_name="Alice", public_response="pub", private_thoughts="priv")
    game.respond_to.side_effect = [_decision("", "r1", "t1"), _decision("", "r2", "t2")]

    def logic(player, target_agent, _response):
        return (f"{player.name} -> {target_agent.name}", target_agent)

    game.run_targeted_round(
        "intro",
        "{player_name}",
        "instruction",
        logic,
        lambda _player: object(),
        validate_name=True,
    )

    board.host_broadcast.assert_any_call("Alice -> Bob")
    board.host_broadcast.assert_any_call("Bob -> Alice")