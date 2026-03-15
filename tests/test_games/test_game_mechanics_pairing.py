from types import SimpleNamespace

from core.game_config import GameConfig
from core.gameboard import GameBoard
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from tests.helpers.game_test_helpers import NoopGameMaster, QueuedClient, TestGameSink, make_debater, turn_payload


def test_handle_manual_pairing_uses_configured_name_field_target_name():
    chooser_client = QueuedClient([turn_payload(target_name="Bob")])
    bob_client = QueuedClient([])
    cara_client = QueuedClient([])

    chooser = make_debater("Alice", chooser_client)
    bob = make_debater("Bob", bob_client)
    cara = make_debater("Cara", cara_client)

    game_board = GameBoard(NoopGameMaster(), TestGameSink())
    game_board.initialize_agents([chooser, bob, cara])
    simulation = SimpleNamespace(agents=[chooser, bob, cara], gameplay_config=GameConfig())
    game = GameMechanicsMixin(game_board, simulation)

    game.get_strategic_players = lambda available_agents, _top_player: [chooser]
    available = [chooser, bob, cara]

    pair = game._handle_manual_pairing(available, loser_picks_first=True)

    assert pair == (chooser, bob)
    assert chooser_client.calls
    assert "target_name" in chooser_client.calls[0]["response_model"].model_fields
