from prompts.votePrompts import VotePromptLibrary
from tests.helpers.game_test_helpers import build_vote_game, host_messages, messages_for, turn_payload


def test_eliminate_player_by_name_removes_player_and_collects_final_words():
    game, board, _agents, clients = build_vote_game(
        {
            "Alice": [],
            "Bob": [turn_payload(public_response="goodbye", private_thoughts="last thought")],
        },
        execution_style=False,
    )

    game.eliminate_player_by_name("Bob")

    assert host_messages(board)[0] == VotePromptLibrary.elimination_host_msg.format(victim_name="Bob")
    assert [agent.name for agent in game.simulationEngine.agents] == ["Alice"]
    assert "Bob" in board.removed_agent_names
    assert len(clients["Bob"].calls) == 1


def test_eliminate_player_by_name_broadcasts_execution_when_enabled():
    game, board, _agents, _clients = build_vote_game(
        {
            "Alice": [],
            "Bob": [turn_payload(public_response="bye", private_thoughts="...")],
        },
        execution_style=True,
    )
    game.get_execution_string = lambda _victim: "EXECUTION_SCENE"

    game.eliminate_player_by_name("Bob")

    system_msgs = messages_for(board, "SYSTEM")
    assert "EXECUTION_SCENE" in system_msgs


def test_eliminate_player_by_name_not_found_is_noop():
    game, board, _agents, clients = build_vote_game({"Alice": []})

    game.eliminate_player_by_name("Bob")

    assert [agent.name for agent in game.simulationEngine.agents] == ["Alice"]
    assert host_messages(board) == []
    assert clients["Alice"].calls == []
