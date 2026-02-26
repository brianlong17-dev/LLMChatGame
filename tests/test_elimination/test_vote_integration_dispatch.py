from core.gameplay_definitions_config import EACH_PLAYER_VOTES_TO_REMOVE
from tests.helpers.game_test_helpers import build_vote_game, turn_payload


def test_vote_definition_dispatch_runs_vote_and_applies_elimination_side_effects():
    manager, board, _agents, clients = build_vote_game(
        {
            "Alice": [],
            "Bob": [turn_payload(public_response="bye", private_thoughts="...")],
            "Cara": [],
        }
    )
    manager.process_vote_rounds = lambda _players: ("Bob", [])

    EACH_PLAYER_VOTES_TO_REMOVE.execute_game(manager, immunity_players=[])

    assert [agent.name for agent in manager.simulationEngine.agents] == ["Alice", "Cara"]
    assert "Bob" in board.removed_agent_names
    assert len(clients["Bob"].calls) == 1
