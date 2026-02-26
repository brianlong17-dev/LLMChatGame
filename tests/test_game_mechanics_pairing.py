from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.game_mechanicsMixin import GameMechanicsMixin


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_handle_manual_pairing_uses_configured_name_field_target_name(monkeypatch):
    chooser = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")

    game_board = MagicMock()
    simulation = SimpleNamespace(agents=[chooser, bob, cara])
    game = GameMechanicsMixin(game_board, simulation)

    game.get_strategic_player = MagicMock(return_value=chooser)
    game.publicPrivateResponse = MagicMock()
    game._choose_name_field = MagicMock(return_value={"target_name": (str, "field")})

    mock_model = object()
    monkeypatch.setattr(
        "gameplay_management.game_mechanicsMixin.DynamicModelFactory.create_model_",
        MagicMock(return_value=mock_model),
    )

    chooser.take_turn_standard.return_value = SimpleNamespace(
        target_name="Bob",
        public_response="pub",
        private_thoughts="priv",
    )

    pair = game._handle_manual_pairing([chooser, bob, cara], winner_picks_first=True)

    assert pair == (chooser, bob)
