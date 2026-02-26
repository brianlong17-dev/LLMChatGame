from prompts.votePrompts import VotePromptLibrary
from tests.helpers.game_test_helpers import build_vote_game, turn_payload


def test_vote_one_player_off_builds_model_and_submits_turn():
    game, _board, agents, clients = build_vote_game(
        {"Alice": [turn_payload(target_name="Bob", public_response="pub", private_thoughts="priv")]}
    )
    alice = agents[0]
    eligible = ["Bob", "Cara"]

    result = game.voteOnePlayerOff(alice, eligible)

    expected_user_content = VotePromptLibrary.vote_one_player_user_content.format(
        eligible_player_names="Bob, Cara"
    )
    assert result.target_name == "Bob"
    assert len(clients["Alice"].calls) == 1
    call = clients["Alice"].calls[0]
    assert expected_user_content in call["messages"][1]["content"]
    assert "target_name" in call["response_model"].model_fields
