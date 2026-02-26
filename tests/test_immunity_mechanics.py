from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin


def test_get_highest_points_players_immunity_returns_all_tied_leaders():
    game_board = MagicMock()
    game_board.agent_scores = {"Alice": 5, "Bob": 7, "Cara": 7, "Dan": 1}
    simulation = SimpleNamespace(agents=[])

    game = ImmunityMechanicsMixin(game_board, simulation)

    result = game.get_highest_points_players_immunity()

    assert result == ["Bob", "Cara"]


def test_get_highest_points_players_immunity_only_one_selects_single_on_tie(monkeypatch):
    game_board = MagicMock()
    game_board.agent_scores = {"Alice": 8, "Bob": 8, "Cara": 2}
    simulation = SimpleNamespace(agents=[])

    game = ImmunityMechanicsMixin(game_board, simulation)

    monkeypatch.setattr(
        "gameplay_management.immunity_mechanicsMixin.random.choice",
        lambda items: items[1],
    )

    result = game.get_highest_points_players_immunity_only_one()

    assert result == ["Bob"]


def test_get_wildcard_player_immunity_queries_chaotic_trait_and_returns_target():
    game_board = MagicMock()
    game_board.agent_names = ["Alice", "Bob", "Cara"]
    game_board.game_master = MagicMock()
    game_board.game_master.choose_agent_based_on_parameter.return_value = SimpleNamespace(target_name="Cara")
    simulation = SimpleNamespace(agents=[])

    game = ImmunityMechanicsMixin(game_board, simulation)

    result = game.get_wildcard_player_immunity()

    game_board.game_master.choose_agent_based_on_parameter.assert_called_once_with(
        game_board,
        ["Alice", "Bob", "Cara"],
        "chaotic",
    )
    assert result == ["Cara"]


def test_get_wildcard_player_random_trait_uses_selected_trait(monkeypatch):
    game_board = MagicMock()
    game_board.agent_names = ["Alice", "Bob"]
    game_board.game_master = MagicMock()
    game_board.game_master.choose_agent_based_on_parameter.return_value = SimpleNamespace(target_name="Alice")
    simulation = SimpleNamespace(agents=[])

    game = ImmunityMechanicsMixin(game_board, simulation)

    monkeypatch.setattr(
        "gameplay_management.immunity_mechanicsMixin.random.choice",
        lambda items: "calculating",
    )

    result = game.get_wildcard_player_random_trait()

    game_board.game_master.choose_agent_based_on_parameter.assert_called_once_with(
        game_board,
        ["Alice", "Bob"],
        "calculating",
    )
    assert result == ["Alice"]
