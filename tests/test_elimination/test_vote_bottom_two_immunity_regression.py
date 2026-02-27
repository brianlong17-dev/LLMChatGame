from tests.helpers.game_test_helpers import build_vote_game


def test_bottom_two_multiple_accepts_immunity_name_list_without_type_crash():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": [], "Dan": []},
        initial_scores={"Alice": 10, "Bob": 1, "Cara": 2, "Dan": 3},
    )
    seen = {"process_players": []}

    game.process_vote_rounds = lambda players: (
        seen["process_players"].append(list(players)) or ("Bob", [])
    )
    game.eliminate_player_by_name = lambda _name: None
    game._dispense_victim_points = lambda _victim, _votes: None

    game.run_voting_bottom_two_multiple(immunity_players=["Alice"])

    assert seen["process_players"] == [["Bob", "Cara"]]


def test_all_vote_modes_accept_name_based_immunity_lists():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": [], "Dan": []},
        initial_scores={"Alice": 9, "Bob": 1, "Cara": 2, "Dan": 3},
    )
    seen = {"process": []}

    game.process_vote_rounds = lambda players: (seen["process"].append(list(players)) or ("Bob", []))
    game.eliminate_player_by_name = lambda _name: None
    game._dispense_victim_points = lambda _victim, _votes: None

    game.run_voting_round_basic(immunity_players=["Alice"])
    game.run_voting_bottom_two_only_two(immunity_players=["Alice"])
    game.run_voting_bottom_two_multiple(immunity_players=["Alice"])

    assert seen["process"][0] == ["Bob", "Cara", "Dan"]
    assert seen["process"][1] == ["Bob", "Cara"]
    assert seen["process"][2] == ["Bob", "Cara"]

