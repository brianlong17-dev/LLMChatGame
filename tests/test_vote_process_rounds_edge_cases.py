from types import SimpleNamespace
from unittest.mock import MagicMock

from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.votePrompts import VotePromptLibrary


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_process_vote_rounds_no_valid_votes_random_elimination_instead_of_crash(monkeypatch):
    alice = _player("Alice")
    bob = _player("Bob")
    simulation = SimpleNamespace(agents=[alice, bob])

    game_board = MagicMock()
    game = VoteMechanicsMixin(game_board, simulation)

    collected_results = [SimpleNamespace(action=""), SimpleNamespace(action=" ")]
    game._collect_votes = MagicMock(return_value=([], collected_results))
    monkeypatch.setattr("gameplay_management.vote_mechanicsMixin.random.choice", lambda players: players[1])

    victim_name, returned_votes = game.process_vote_rounds(["Alice", "Bob"])

    assert victim_name == "Bob"
    assert returned_votes == collected_results

    broadcast_messages = [c.args[0] for c in game_board.host_broadcast.call_args_list]
    assert VotePromptLibrary.voting_tally_msg.format(tally="") in broadcast_messages
    assert VotePromptLibrary.voting_round_no_valid_votes_msg in broadcast_messages
