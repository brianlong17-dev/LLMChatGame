from tests.helpers.game_test_helpers import build_vote_game, host_messages, turn_payload


def test_run_voting_winner_chooses_selects_target_and_eliminates():
    game, board, agents, _clients = build_vote_game(
        {
            "Alice": [turn_payload(target_name="Bob")],
            "Bob": [],
            "Cara": [],
        }
    )
    alice = agents[0]
    eliminated = []

    game._validate_immunity = lambda immunity: []
    game.get_strategic_player = lambda _agents, top_player=True: alice
    game.eliminate_player_by_name = lambda name: eliminated.append(name)

    game.run_voting_winner_chooses()

    expected = "Alice"
    assert expected in host_messages(board)[0]
    assert eliminated == ["Bob"]


def test_run_voting_lowest_points_removed_announces_and_eliminates_lowest():
    game, board, agents, _clients = build_vote_game(
        {"Alice": [], "Bob": []},
        initial_scores={"Alice": 5, "Bob": 1},
    )
    bob = next(a for a in agents if a.name == "Bob")
    eliminated = []
    game.get_strategic_player = lambda _agents, top_player=False: bob
    game.eliminate_player_by_name = lambda name: eliminated.append(name)

    game.run_voting_lowest_points_removed()

    assert "Bob" in host_messages(board)[0]
    assert eliminated == ["Bob"]


def test_run_voting_round_basic_dont_miss_forwards_to_basic_with_flag():
    game, _board, _agents, _clients = build_vote_game({})
    seen = []
    game.run_voting_round_basic = lambda immunity_players, dont_miss=False: seen.append(
        (immunity_players, dont_miss)
    )

    game.run_voting_round_basic_dont_miss(["Alice"])

    assert seen == [(["Alice"], True)]
