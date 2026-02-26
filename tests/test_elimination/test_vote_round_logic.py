from types import SimpleNamespace

from prompts.votePrompts import VotePromptLibrary
from tests.helpers.game_test_helpers import build_vote_game, host_messages


def test_process_vote_rounds_returns_clear_winner():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})

    def _collect(players_up_for_elimination):
        assert players_up_for_elimination == ["Alice", "Bob", "Cara"]
        return ["Bob", "Alice", "Bob"], [SimpleNamespace(action="x")]

    game._collect_votes = _collect
    victim_name, returned_votes = game.process_vote_rounds(["Alice", "Bob", "Cara"])

    assert victim_name == "Bob"
    assert returned_votes == [SimpleNamespace(action="x")]
    assert host_messages(board)[-1] == VotePromptLibrary.voting_tally_msg.format(
        tally="Bob: 2 votes, Alice: 1 votes"
    )


def test_process_vote_rounds_tie_revotes_on_tied_subset_only():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": [], "Dan": []})
    calls = []

    def _collect(players_up_for_elimination):
        calls.append(list(players_up_for_elimination))
        if len(calls) == 1:
            return ["Alice", "Bob", "Alice", "Bob"], [SimpleNamespace(action="round1")]
        return ["Bob", "Bob", "Alice", "Bob"], [SimpleNamespace(action="round2")]

    game._collect_votes = _collect
    victim_name, returned_votes = game.process_vote_rounds(["Alice", "Bob", "Cara", "Dan"])

    assert victim_name == "Bob"
    assert returned_votes == [SimpleNamespace(action="round1")]
    assert calls == [["Alice", "Bob", "Cara", "Dan"], ["Alice", "Bob"]]
    assert any("tie between Alice, Bob" in m for m in host_messages(board))


def test_process_vote_rounds_complete_deadlock_uses_deadlock_message():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    calls = {"count": 0}

    def _collect(_players_up_for_elimination):
        calls["count"] += 1
        if calls["count"] == 1:
            return ["Alice", "Bob", "Cara"], [SimpleNamespace(action="round1")]
        return ["Bob", "Bob", "Alice"], [SimpleNamespace(action="round2")]

    game._collect_votes = _collect
    victim_name, _ = game.process_vote_rounds(["Alice", "Bob", "Cara"])

    assert victim_name == "Bob"
    assert VotePromptLibrary.voting_round_complete_deadlock_msg.format(max_votes=1) in host_messages(board)


def test_process_vote_rounds_after_max_revotes_randomly_eliminates(monkeypatch):
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": []})
    initial_votes = [SimpleNamespace(action="Alice")]
    monkeypatch.setattr("gameplay_management.vote_mechanicsMixin.random.choice", lambda players: players[1])

    victim_name, returned_votes = game.process_vote_rounds(
        ["Alice", "Bob"], revote_count=4, initial_votes=initial_votes
    )

    assert victim_name == "Bob"
    assert returned_votes == initial_votes
    assert host_messages(board)[-1] == VotePromptLibrary.voting_round_random_elimination_msg


def test_process_vote_rounds_uses_explicit_initial_votes_if_provided():
    game, _board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    collected_results = [SimpleNamespace(action="Bob")]
    preserved_initial_votes = [SimpleNamespace(action="Alice"), SimpleNamespace(action="Bob")]
    game._collect_votes = lambda _players: (["Bob", "Alice", "Bob"], collected_results)

    victim_name, returned_votes = game.process_vote_rounds(
        ["Alice", "Bob", "Cara"], initial_votes=preserved_initial_votes
    )

    assert victim_name == "Bob"
    assert returned_votes == preserved_initial_votes
