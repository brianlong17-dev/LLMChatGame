from types import SimpleNamespace

from tests.helpers.game_test_helpers import build_vote_game, host_messages


def test_run_voting_round_basic_broadcasts_and_eliminates_without_dont_miss():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    calls = {"process": [], "eliminate": [], "dispense": []}

    game._validate_immunity = lambda immunity: ["Alice"]
    game.immunity_string = lambda immunity, players: "IMMUNITY_BLOCK"
    game.process_vote_rounds = lambda players: (
        calls["process"].append(list(players)) or ("Bob", [SimpleNamespace(action="Bob")])
    )
    game._dispense_victim_points = lambda victim, votes: calls["dispense"].append((victim, votes))
    game.eliminate_player_by_name = lambda victim: calls["eliminate"].append(victim)

    game.run_voting_round_basic(immunity_players=["Alice"], dont_miss=False)

    assert calls["process"] == [["Bob", "Cara"]]
    assert calls["dispense"] == []
    assert calls["eliminate"] == ["Bob"]
    message = host_messages(board)[0]
    assert "IT'S TIME TO VOTE" in message
    assert "IMMUNITY_BLOCK" in message
    assert "vote will automatically count as a vote against YOURSELF" in message


def test_run_voting_round_basic_calls_dont_miss_dispense_when_enabled():
    game, _board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    calls = {"process": [], "eliminate": [], "dispense": []}
    voting_results = [SimpleNamespace(action="Alice"), SimpleNamespace(action="Bob")]

    game._validate_immunity = lambda immunity: []
    game.immunity_string = lambda immunity, players: "ELIGIBLE_BLOCK"
    game.process_vote_rounds = lambda players: (calls["process"].append(list(players)) or ("Bob", voting_results))
    game._dispense_victim_points = lambda victim, votes: calls["dispense"].append((victim, votes))
    game.eliminate_player_by_name = lambda victim: calls["eliminate"].append(victim)

    game.run_voting_round_basic(immunity_players=None, dont_miss=True)

    assert calls["process"] == [["Alice", "Bob", "Cara"]]
    assert calls["dispense"] == [("Bob", voting_results)]
    assert calls["eliminate"] == ["Bob"]
