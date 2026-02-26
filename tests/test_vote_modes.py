from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.votePrompts import VotePromptLibrary


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_run_voting_winner_chooses_selects_target_and_eliminates(monkeypatch):
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game_board.agent_names = ["Alice", "Bob", "Cara"]

    game = VoteMechanicsMixin(game_board, simulation)
    game._validate_immunity = MagicMock(return_value=[])
    game.get_strategic_player = MagicMock(return_value=alice)
    game.create_choice_field = MagicMock(return_value={"target_name": (str, "field")})
    game.publicPrivateResponse = MagicMock()
    game.eliminate_player_by_name = MagicMock()

    model_obj = object()
    monkeypatch.setattr(
        "gameplay_management.vote_mechanicsMixin.DynamicModelFactory.create_model_",
        MagicMock(return_value=model_obj),
    )

    response = SimpleNamespace(target_name="Bob", public_response="pub", private_thoughts="priv")
    alice.take_turn_standard.return_value = response

    game.run_voting_winner_chooses()

    expected_host_msg = VotePromptLibrary.winner_chooses_host_msg.format(
        leading_player_name="Alice",
        other_agent_names="Bob, Cara",
    )
    game_board.host_broadcast.assert_called_once_with(expected_host_msg)

    game.create_choice_field.assert_called_once_with(
        "target_name",
        ["Bob", "Cara"],
        field_description=VotePromptLibrary.winner_chooses_choice_prompt,
    )

    assert alice.take_turn_standard.call_args.args[0] == VotePromptLibrary.winner_chooses_context_msg
    game.publicPrivateResponse.assert_called_once_with(alice, response)
    game.eliminate_player_by_name.assert_called_once_with("Bob")


def test_run_voting_lowest_points_removed_announces_and_eliminates_lowest():
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    game.get_strategic_player = MagicMock(return_value=bob)
    game.eliminate_player_by_name = MagicMock()

    game.run_voting_lowest_points_removed()

    game.get_strategic_player.assert_called_once_with(simulation.agents, top_player=False)
    game_board.host_broadcast.assert_called_once()
    assert "Bob" in game_board.host_broadcast.call_args.args[0]
    game.eliminate_player_by_name.assert_called_once_with("Bob")


def test_run_voting_round_basic_dont_miss_forwards_to_basic_with_flag():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[])
    game = VoteMechanicsMixin(game_board, simulation)

    game.run_voting_round_basic = MagicMock()

    game.run_voting_round_basic_dont_miss(["Alice"])

    game.run_voting_round_basic.assert_called_once_with(["Alice"], dont_miss=True)
