from types import SimpleNamespace

from tests.helpers.game_test_helpers import build_vote_game, host_messages


def test_dispense_victim_points_awards_survivors_and_broadcasts_summary():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    voting_results = [
        SimpleNamespace(target_name="Bob"),
        SimpleNamespace(target_name=" Alice "),
        SimpleNamespace(target_name="Alice"),
        SimpleNamespace(target_name="Cara"),
    ]

    game._dispense_victim_points("Bob", voting_results)

    assert board.agent_scores == {"Alice": 2, "Bob": 0, "Cara": 1}
    message = host_messages(board)[-1]
    assert "Alice (+2)" in message
    assert "Cara (+1)" in message


def test_dispense_victim_points_no_survivors_no_broadcast():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": []})
    voting_results = [
        SimpleNamespace(target_name="Bob"),
        SimpleNamespace(target_name=" Bob "),
        SimpleNamespace(target_name=""),
        SimpleNamespace(target_name="   "),
    ]

    game._dispense_victim_points("Bob", voting_results)

    assert board.agent_scores == {"Alice": 0, "Bob": 0}
    assert host_messages(board) == []
