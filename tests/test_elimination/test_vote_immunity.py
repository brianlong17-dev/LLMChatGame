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


def test_immunity_string_includes_immune_and_eligible_names():
    game, _board, _agents, _clients = build_vote_game({"Alice": [], "Bob": [], "Cara": []})
    text = game.immunity_string(["Alice"], ["Bob", "Cara"])
    assert "Alice" in text
    assert "Bob" in text
    assert "Cara" in text
    assert VotePromptLibrary.immunity_players_prefix in text
    assert VotePromptLibrary.elimination_players_prefix in text
