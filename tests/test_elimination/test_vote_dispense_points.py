from types import SimpleNamespace
from unittest.mock import MagicMock, call

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin


def test_dispense_victim_points_awards_survivors_and_broadcasts_summary():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[])
    game = VoteMechanicsMixin(game_board, simulation)

    voting_results = [
        SimpleNamespace(target_name="Bob"),
        SimpleNamespace(target_name=" Alice "),
        SimpleNamespace(target_name="Alice"),
        SimpleNamespace(target_name="Cara"),
    ]

    game._dispense_victim_points("Bob", voting_results)

    game_board.append_agent_points.assert_has_calls(
        [call("Alice", 1), call("Alice", 1), call("Cara", 1)],
        any_order=False,
    )
    game_board.host_broadcast.assert_called_once()
    message = game_board.host_broadcast.call_args.args[0]
    assert "Alice (+2)" in message
    assert "Cara (+1)" in message


def test_dispense_victim_points_no_survivors_no_broadcast():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[])
    game = VoteMechanicsMixin(game_board, simulation)

    voting_results = [
        SimpleNamespace(target_name="Bob"),
        SimpleNamespace(target_name=" Bob "),
        SimpleNamespace(target_name=""),
        SimpleNamespace(target_name="   "),
    ]

    game._dispense_victim_points("Bob", voting_results)

    game_board.append_agent_points.assert_not_called()
    game_board.host_broadcast.assert_not_called()


def test_dispense_victim_points_reads_configured_name_field_target_name():
    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[])
    game = VoteMechanicsMixin(game_board, simulation)

    voting_results = [
        SimpleNamespace(target_name="Bob"),
        SimpleNamespace(target_name=" Alice "),
        SimpleNamespace(target_name="Alice"),
        SimpleNamespace(target_name="Cara"),
    ]

    game._dispense_victim_points("Bob", voting_results)

    game_board.append_agent_points.assert_has_calls(
        [call("Alice", 1), call("Alice", 1), call("Cara", 1)],
        any_order=False,
    )
    game_board.host_broadcast.assert_called_once()
