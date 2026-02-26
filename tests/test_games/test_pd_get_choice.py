from types import SimpleNamespace

from core.gameboard import GameBoard
from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
from tests.helpers.game_test_helpers import NoopGameMaster, QueuedClient, make_debater


def test_get_split_or_steal_flow():
    player_client = QueuedClient(
        [{"action": "split", "public_response": "pub", "private_thoughts": "priv"}]
    )
    opponent_client = QueuedClient([])
    player = make_debater("Hero", player_client)
    opponent = make_debater("Villain", opponent_client)

    board = GameBoard(NoopGameMaster())
    board.initialize_agents([player, opponent])
    simulation = SimpleNamespace(agents=[player, opponent])
    pd_game = GamePrisonersDilemma(board, simulation)

    result = pd_game.get_split_or_steal(player, opponent)

    assert result.action == "split"
    assert len(player_client.calls) == 1
    call = player_client.calls[0]
    assert "Villain" in call["messages"][1]["content"]
    assert "action" in call["response_model"].model_fields
