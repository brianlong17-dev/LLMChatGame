from tests.helpers.game_test_helpers import build_vote_game, turn_payload


def test_collect_votes_counts_valid_votes_and_strips_whitespace():
    game, _board, _agents, clients = build_vote_game(
        {
            "Alice": [turn_payload(target_name=" Bob ")],
            "Bob": [turn_payload(target_name="Alice")],
            "Cara": [turn_payload(target_name="Bob")],
        }
    )

    votes, voting_results = game._collect_votes(["Alice", "Bob", "Cara"])

    assert votes == ["Bob", "Alice", "Bob"]
    assert [r.target_name for r in voting_results] == [" Bob ", "Alice", "Bob"]
    for client in clients.values():
        client.assert_exhausted()


def test_collect_votes_invalid_vote_counts_as_self_when_pass_not_allowed():
    game, _board, _agents, _clients = build_vote_game(
        {
            "Alice": [turn_payload(target_name="NotAPlayer")],
            "Bob": [turn_payload(target_name="Alice")],
        }
    )

    votes, _ = game._collect_votes(["Alice", "Bob"], pass_allowed=False)
    assert votes == ["Alice", "Alice"]


def test_collect_votes_invalid_vote_is_skipped_when_pass_allowed():
    game, _board, _agents, _clients = build_vote_game(
        {
            "Alice": [turn_payload(target_name="NotAPlayer")],
            "Bob": [turn_payload(target_name="Alice")],
        }
    )

    votes, _ = game._collect_votes(["Alice", "Bob"], pass_allowed=True)
    assert votes == ["Alice"]
