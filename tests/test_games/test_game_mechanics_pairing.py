from types import SimpleNamespace

from core.gameboard import GameBoard
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from tests.helpers.game_test_helpers import NoopGameMaster, QueuedClient, make_debater, turn_payload


def test_handle_manual_pairing_uses_configured_name_field_target_name():
    chooser_client = QueuedClient([turn_payload(target_name="Bob")])
    bob_client = QueuedClient([])
    cara_client = QueuedClient([])

    chooser = make_debater("Alice", chooser_client)
    bob = make_debater("Bob", bob_client)
    cara = make_debater("Cara", cara_client)

    game_board = GameBoard(NoopGameMaster())
    game_board.initialize_agents([chooser, bob, cara])
    simulation = SimpleNamespace(agents=[chooser, bob, cara])
    game = GameMechanicsMixin(game_board, simulation)

    game.get_strategic_player = lambda available_agents, _winner_picks_first: chooser
    available = [chooser, bob, cara]

    pair = game._handle_manual_pairing(available, winner_picks_first=True)

    assert pair == (chooser, bob)
    assert chooser_client.calls
    assert "target_name" in chooser_client.calls[0]["response_model"].model_fields
