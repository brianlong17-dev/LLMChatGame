from types import SimpleNamespace
from unittest.mock import MagicMock, call

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def _vote(action, public_response="pub", private_thoughts="priv"):
    return SimpleNamespace(target_name=action, public_response=public_response, private_thoughts=private_thoughts)


def test_collect_votes_counts_valid_votes_and_strips_whitespace():
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    alice_vote = _vote(" Bob ")
    bob_vote = _vote("Alice")
    cara_vote = _vote("Bob")
    vote_map = {"Alice": alice_vote, "Bob": bob_vote, "Cara": cara_vote}

    game.voteOnePlayerOff = MagicMock(side_effect=lambda agent, _eligible: vote_map[agent.name])
    game.publicPrivateResponse = MagicMock()

    votes, voting_results = game._collect_votes(["Alice", "Bob", "Cara"])

    assert votes == ["Bob", "Alice", "Bob"]
    assert voting_results == [alice_vote, bob_vote, cara_vote]
    game.publicPrivateResponse.assert_has_calls(
        [call(alice, alice_vote), call(bob, bob_vote), call(cara, cara_vote)],
        any_order=False,
    )


def test_collect_votes_invalid_vote_counts_as_self_when_pass_not_allowed():
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    alice_vote = _vote("NotAPlayer")
    bob_vote = _vote("Alice")
    vote_map = {"Alice": alice_vote, "Bob": bob_vote}

    game.voteOnePlayerOff = MagicMock(side_effect=lambda agent, _eligible: vote_map[agent.name])
    game.publicPrivateResponse = MagicMock()

    votes, _ = game._collect_votes(["Alice", "Bob"], pass_allowed=False)

    assert votes == ["Alice", "Alice"]
    game.publicPrivateResponse.assert_has_calls(
        [call(alice, alice_vote), call(bob, bob_vote)],
        any_order=False,
    )


def test_collect_votes_invalid_vote_is_skipped_when_pass_allowed():
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    alice_vote = _vote("NotAPlayer")
    bob_vote = _vote("Alice")
    vote_map = {"Alice": alice_vote, "Bob": bob_vote}

    game.voteOnePlayerOff = MagicMock(side_effect=lambda agent, _eligible: vote_map[agent.name])
    game.publicPrivateResponse = MagicMock()

    votes, _ = game._collect_votes(["Alice", "Bob"], pass_allowed=True)

    assert votes == ["Alice"]
    game.publicPrivateResponse.assert_has_calls(
        [call(alice, alice_vote), call(bob, bob_vote)],
        any_order=False,
    )


def test_collect_votes_reads_configured_name_field_target_name():
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    alice_vote = SimpleNamespace(target_name=" Bob ", public_response="pub", private_thoughts="priv")
    bob_vote = SimpleNamespace(target_name="Alice", public_response="pub", private_thoughts="priv")
    vote_map = {"Alice": alice_vote, "Bob": bob_vote}

    game.voteOnePlayerOff = MagicMock(side_effect=lambda agent, _eligible: vote_map[agent.name])
    game.publicPrivateResponse = MagicMock()

    votes, voting_results = game._collect_votes(["Alice", "Bob"])

    assert votes == ["Bob", "Alice"]
    assert voting_results == [alice_vote, bob_vote]
    game.publicPrivateResponse.assert_has_calls(
        [call(alice, alice_vote), call(bob, bob_vote)],
        any_order=False,
    )
