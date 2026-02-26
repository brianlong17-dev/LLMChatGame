from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_run_voting_round_basic_broadcasts_and_eliminates_without_dont_miss():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    game._validate_immunity = MagicMock(return_value=["Alice"])
    game.immunity_string = MagicMock(return_value="IMMUNITY_BLOCK")

    voting_results = [SimpleNamespace(action="Bob"), SimpleNamespace(action="Bob")]
    game.process_vote_rounds = MagicMock(return_value=("Bob", voting_results))
    game._dispense_victim_points = MagicMock()
    game.eliminate_player_by_name = MagicMock()

    game.run_voting_round_basic(immunity_players=["Alice"], dont_miss=False)

    game.process_vote_rounds.assert_called_once_with(["Bob", "Cara"])
    game._dispense_victim_points.assert_not_called()
    game.eliminate_player_by_name.assert_called_once_with("Bob")

    game_board.host_broadcast.assert_called_once()
    host_message = game_board.host_broadcast.call_args.args[0]
    assert "IT'S TIME TO VOTE" in host_message
    assert "IMMUNITY_BLOCK" in host_message
    assert "vote will automatically count as a vote against YOURSELF" in host_message


def test_run_voting_round_basic_calls_dont_miss_dispense_when_enabled():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    game._validate_immunity = MagicMock(return_value=[])
    game.immunity_string = MagicMock(return_value="ELIGIBLE_BLOCK")

    voting_results = [SimpleNamespace(action="Alice"), SimpleNamespace(action="Bob")]
    game.process_vote_rounds = MagicMock(return_value=("Bob", voting_results))
    game._dispense_victim_points = MagicMock()
    game.eliminate_player_by_name = MagicMock()

    game.run_voting_round_basic(immunity_players=None, dont_miss=True)

    game.process_vote_rounds.assert_called_once_with(["Alice", "Bob", "Cara"])
    game._dispense_victim_points.assert_called_once_with("Bob", voting_results)
    game.eliminate_player_by_name.assert_called_once_with("Bob")
