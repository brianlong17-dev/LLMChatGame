from types import SimpleNamespace
from unittest.mock import MagicMock, call

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.votePrompts import VotePromptLibrary


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_process_vote_rounds_returns_clear_winner():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    voting_results = [SimpleNamespace(action="Bob"), SimpleNamespace(action="Alice"), SimpleNamespace(action="Bob")]
    game._collect_votes = MagicMock(return_value=(["Bob", "Alice", "Bob"], voting_results))

    victim_name, returned_votes = game.process_vote_rounds(["Alice", "Bob", "Cara"])

    assert victim_name == "Bob"
    assert returned_votes == voting_results
    game._collect_votes.assert_called_once_with(["Alice", "Bob", "Cara"])
    game_board.host_broadcast.assert_called_once_with(
        VotePromptLibrary.voting_tally_msg.format(tally="Bob: 2 votes, Alice: 1 votes")
    )


def test_process_vote_rounds_tie_revotes_on_tied_subset_only():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    dan = _player("Dan")
    simulation = SimpleNamespace(agents=[alice, bob, cara, dan])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    first_round_results = [
        SimpleNamespace(action="Alice"),
        SimpleNamespace(action="Bob"),
        SimpleNamespace(action="Alice"),
        SimpleNamespace(action="Bob"),
    ]
    second_round_results = [
        SimpleNamespace(action="Bob"),
        SimpleNamespace(action="Bob"),
        SimpleNamespace(action="Alice"),
        SimpleNamespace(action="Bob"),
    ]

    game._collect_votes = MagicMock(
        side_effect=[
            (["Alice", "Bob", "Alice", "Bob"], first_round_results),
            (["Bob", "Bob", "Alice", "Bob"], second_round_results),
        ]
    )

    victim_name, returned_votes = game.process_vote_rounds(["Alice", "Bob", "Cara", "Dan"])

    assert victim_name == "Bob"
    # Returned voting_results should preserve initial round votes across revote recursion.
    assert returned_votes == first_round_results
    assert game._collect_votes.call_args_list == [
        call(["Alice", "Bob", "Cara", "Dan"]),
        call(["Alice", "Bob"]),
    ]
    assert VotePromptLibrary.voting_round_tie_msg.format(
        players_with_most_votes="Alice, Bob"
    ) in [c.args[0] for c in game_board.host_broadcast.call_args_list]


def test_process_vote_rounds_complete_deadlock_uses_deadlock_message():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    first_round_results = [
        SimpleNamespace(action="Alice"),
        SimpleNamespace(action="Bob"),
        SimpleNamespace(action="Cara"),
    ]
    second_round_results = [
        SimpleNamespace(action="Bob"),
        SimpleNamespace(action="Bob"),
        SimpleNamespace(action="Alice"),
    ]

    game._collect_votes = MagicMock(
        side_effect=[
            (["Alice", "Bob", "Cara"], first_round_results),
            (["Bob", "Bob", "Alice"], second_round_results),
        ]
    )

    victim_name, _returned_votes = game.process_vote_rounds(["Alice", "Bob", "Cara"])

    assert victim_name == "Bob"
    assert VotePromptLibrary.voting_round_complete_deadlock_msg.format(max_votes=1) in [
        c.args[0] for c in game_board.host_broadcast.call_args_list
    ]


def test_process_vote_rounds_after_max_revotes_randomly_eliminates(monkeypatch):
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    initial_votes = [SimpleNamespace(action="Alice")]
    monkeypatch.setattr("gameplay_management.vote_mechanicsMixin.random.choice", lambda players: players[1])

    victim_name, returned_votes = game.process_vote_rounds(
        ["Alice", "Bob"], revote_count=4, initial_votes=initial_votes
    )

    assert victim_name == "Bob"
    assert returned_votes == initial_votes
    game_board.host_broadcast.assert_called_once_with(VotePromptLibrary.voting_round_random_elimination_msg)


def test_process_vote_rounds_uses_explicit_initial_votes_if_provided():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    collected_results = [SimpleNamespace(action="Bob")]
    preserved_initial_votes = [SimpleNamespace(action="Alice"), SimpleNamespace(action="Bob")]
    game._collect_votes = MagicMock(return_value=(["Bob", "Alice", "Bob"], collected_results))

    victim_name, returned_votes = game.process_vote_rounds(
        ["Alice", "Bob", "Cara"], initial_votes=preserved_initial_votes
    )

    assert victim_name == "Bob"
    assert returned_votes == preserved_initial_votes
