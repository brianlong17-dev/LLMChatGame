from types import SimpleNamespace
from unittest.mock import MagicMock


from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.votePrompts import VotePromptLibrary


def _player(name):
    p = MagicMock()
    p.name = name
    return p


def test_validate_immunity_none_returns_empty_list():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[_player("Alice"), _player("Bob")])
    game = VoteMechanicsMixin(game_board, simulation)

    result = game._validate_immunity(None)

    assert result == []
    game_board.host_broadcast.assert_not_called()


def test_validate_immunity_all_players_immune_clears_and_broadcasts():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[_player("Alice"), _player("Bob"), _player("Cara")])
    game = VoteMechanicsMixin(game_board, simulation)

    result = game._validate_immunity(["Alice", "Bob", "Cara"])

    assert result == []
    game_board.host_broadcast.assert_called_once()
    assert game_board.host_broadcast.call_args.args[0] == VotePromptLibrary.immunity_all_players_reset


def test_immunity_string_includes_immune_and_eligible_names():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[_player("Alice"), _player("Bob"), _player("Cara")])
    game = VoteMechanicsMixin(game_board, simulation)

    text = game.immunity_string(["Alice"], ["Bob", "Cara"])

    assert "Alice" in text
    assert "Bob" in text
    assert "Cara" in text
    assert VotePromptLibrary.immunity_players_prefix in text
    assert VotePromptLibrary.elimination_players_prefix in text
