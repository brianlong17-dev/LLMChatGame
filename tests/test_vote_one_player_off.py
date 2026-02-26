from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.votePrompts import VotePromptLibrary


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_vote_one_player_off_builds_model_and_submits_turn(monkeypatch):
    alice = _player("Alice")
    simulation = SimpleNamespace(agents=[alice])
    game_board = MagicMock()

    game = VoteMechanicsMixin(game_board, simulation)

    action_fields = {"action": (str, "field")}
    game._choose_name_field = MagicMock(return_value=action_fields)

    response_model = object()
    create_model_mock = MagicMock(return_value=response_model)
    monkeypatch.setattr(
        "gameplay_management.vote_mechanicsMixin.DynamicModelFactory.create_model_",
        create_model_mock,
    )

    vote_result = SimpleNamespace(action="Bob", public_response="pub", private_thoughts="priv")
    alice.take_turn_standard.return_value = vote_result

    eligible = ["Bob", "Cara"]
    result = game.voteOnePlayerOff(alice, eligible)

    expected_user_content = VotePromptLibrary.vote_one_player_user_content.format(
        eligible_player_names="Bob, Cara"
    )

    game._choose_name_field.assert_called_once_with(
        eligible,
        VotePromptLibrary.vote_one_player_name_field_prompt,
    )
    create_model_mock.assert_called_once_with(
        alice,
        model_name="vote_out_player",
        action_fields=action_fields,
    )
    alice.take_turn_standard.assert_called_once_with(expected_user_content, game_board, response_model)
    assert result is vote_result
