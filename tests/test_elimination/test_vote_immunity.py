import pytest

from prompts.votePrompts import VotePromptLibrary
from tests.helpers.game_test_helpers import build_vote_game, host_messages


def test_validate_immunity_none_returns_empty_list():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": []})
    assert game._validate_immunity(None) == []
    assert host_messages(board) == []


def test_validate_immunity_all_players_immune_clears_and_broadcasts():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    result = game._validate_immunity(["Alice", "Bob", "Cara"])
    assert result == []
    assert host_messages(board)[-1] == VotePromptLibrary.immunity_all_players_reset


def test_validate_immunity_rejects_non_string_entries():
    game, _board, _agents, _clients = build_vote_game({"Alice": [], "Bob": []})

    with pytest.raises(TypeError, match="must be list\\[str\\]"):
        game._validate_immunity(["Alice", object()])


def test_validate_immunity_dedupes_names_preserving_order():
    game, _board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": [], "Dan": []})

    result = game._validate_immunity(["Alice", "Bob", "Alice", "Cara", "Bob"])

    assert result == ["Alice", "Bob", "Cara"]


def test_run_voting_round_basic_all_players_immune_resets_and_still_votes():
    game, board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    seen = {"process": [], "eliminate": []}

    game.process_vote_rounds = lambda players: (
        seen["process"].append(list(players)) or ("Bob", [])
    )
    game.eliminate_player_by_name = lambda name: seen["eliminate"].append(name)

    game.run_voting_round_basic(immunity_players=["Alice", "Bob", "Cara"])

    assert seen["process"] == [["Alice", "Bob", "Cara"]]
    assert seen["eliminate"] == ["Bob"]
    assert VotePromptLibrary.immunity_all_players_reset in host_messages(board)


def test_immunity_string_includes_immune_and_eligible_names():
    game, _board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    text = game.immunity_string(["Alice"], ["Bob", "Cara"])
    assert "Alice" in text
    assert "Bob" in text
    assert "Cara" in text
    assert VotePromptLibrary.immunity_players_prefix in text
    assert VotePromptLibrary.elimination_players_prefix in text
