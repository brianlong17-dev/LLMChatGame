from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.votePrompts import VotePromptLibrary


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_eliminate_player_by_name_removes_player_and_collects_final_words(monkeypatch):
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game_board.execution_style = False

    game = VoteMechanicsMixin(game_board, simulation)
    game.publicPrivateResponse = MagicMock()

    final_words_result = SimpleNamespace(public_response="goodbye", private_thoughts="last thought")
    game.respond_to = MagicMock(return_value=final_words_result)

    final_prompt_mock = MagicMock(return_value="FINAL_WORDS_PROMPT")
    monkeypatch.setattr("gameplay_management.vote_mechanicsMixin.PromptLibrary.final_words_prompt", final_prompt_mock)

    game.eliminate_player_by_name("Bob")

    game_board.host_broadcast.assert_called_once()
    host_message = game_board.host_broadcast.call_args.args[0]
    assert host_message == VotePromptLibrary.elimination_host_msg.format(victim_name="Bob")

    game_board.remove_agent_state.assert_called_once_with("Bob")
    assert [agent.name for agent in simulation.agents] == ["Alice"]

    final_prompt_mock.assert_called_once_with(game_board)
    game.respond_to.assert_called_once()
    respond_call = game.respond_to.call_args
    assert respond_call.args[0] is bob
    assert respond_call.args[1] == host_message
    assert respond_call.kwargs["instruction_override"] == "FINAL_WORDS_PROMPT"

    game.publicPrivateResponse.assert_called_once_with(bob, final_words_result)
    game_board.system_broadcast.assert_not_called()


def test_eliminate_player_by_name_broadcasts_execution_when_enabled(monkeypatch):
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game_board.execution_style = True

    game = VoteMechanicsMixin(game_board, simulation)
    game.publicPrivateResponse = MagicMock()
    game.respond_to = MagicMock(return_value=SimpleNamespace(public_response="bye", private_thoughts="..."))
    game.get_execution_string = MagicMock(return_value="EXECUTION_SCENE")

    monkeypatch.setattr(
        "gameplay_management.vote_mechanicsMixin.PromptLibrary.final_words_prompt",
        MagicMock(return_value="FINAL_WORDS_PROMPT"),
    )

    game.eliminate_player_by_name("Bob")

    game.get_execution_string.assert_called_once_with(bob)
    game_board.system_broadcast.assert_called_once_with("EXECUTION_SCENE")


def test_eliminate_player_by_name_not_found_is_noop():
    alice = _player("Alice")
    simulation = SimpleNamespace(agents=[alice])

    game_board = MagicMock()
    game_board.execution_style = False

    game = VoteMechanicsMixin(game_board, simulation)
    game.publicPrivateResponse = MagicMock()
    game.respond_to = MagicMock()

    game.eliminate_player_by_name("Bob")

    assert [agent.name for agent in simulation.agents] == ["Alice"]
    game_board.host_broadcast.assert_not_called()
    game_board.remove_agent_state.assert_not_called()
    game.respond_to.assert_not_called()
    game.publicPrivateResponse.assert_not_called()
    game_board.system_broadcast.assert_not_called()
