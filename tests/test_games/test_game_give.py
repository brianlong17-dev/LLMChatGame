from typing import get_args

import pytest

from tests.helpers.game_test_helpers import (
    build_targeted_choice_game,
    host_messages,
    turn_payload,
)


@pytest.fixture
def build_game():
    return build_targeted_choice_game


def test_give_awards_points_to_selected_target_for_each_turn(build_game):
    game, board, _agents, clients = build_game(
        {
            "Alice": [
                turn_payload(target_name="Bob", public_response="Alice gives to Bob"),
                turn_payload(public_response="Alice reacts to Bob giving"),
            ],
            "Bob": [
                turn_payload(public_response="Bob reacts to Alice giving"),
                turn_payload(target_name="Alice", public_response="Bob gives to Alice"),
            ],
        }
    )

    game.run_game_give()

    assert board.agent_scores == {"Alice": 3, "Bob": 3}
    messages = host_messages(board)
    assert "Yay! Alice chooses Bob! They receive 3 points." in messages
    assert "Yay! Bob chooses Alice! They receive 3 points." in messages
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_give_invalid_self_choice_gets_no_points_and_self_reacts(build_game):
    game, board, _agents, clients = build_game(
        {
            "Alice": [
                turn_payload(target_name="Alice", public_response="I pick myself"),
                turn_payload(public_response="I react to my invalid target"),
                turn_payload(public_response="I react to Bob giving me points"),
            ],
            "Bob": [
                turn_payload(target_name="Alice", public_response="I pick Alice"),
            ],
        }
    )

    game.run_game_give()

    assert board.agent_scores == {"Alice": 3, "Bob": 0}
    messages = host_messages(board)
    invalid_messages = [m for m in messages if "invalid target" in m]
    assert len(invalid_messages) == 1
    assert "Alice chose 'Alice'" in invalid_messages[0]
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_give_unknown_name_is_invalid_and_scores_nothing(build_game):
    game, board, _agents, clients = build_game(
        {
            "Alice": [
                turn_payload(target_name="NotAPlayer"),
                turn_payload(public_response="Alice reacts"),
            ],
            "Bob": [
                turn_payload(target_name="StillNotAPlayer"),
                turn_payload(public_response="Bob reacts"),
            ],
        }
    )

    game.run_game_give()

    assert board.agent_scores == {"Alice": 0, "Bob": 0}
    invalid_messages = [m for m in host_messages(board) if "invalid target" in m]
    assert len(invalid_messages) == 2
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_give_model_choices_exclude_current_player(build_game):
    game, _board, _agents, clients = build_game(
        {
            "Alice": [
                turn_payload(target_name="Bob"),
                turn_payload(public_response="Alice reacts"),
            ],
            "Bob": [
                turn_payload(public_response="Bob reacts"),
                turn_payload(target_name="Cara"),
            ],
            "Cara": [
                turn_payload(public_response="Cara reacts"),
                turn_payload(target_name="Alice"),
            ],
        }
    )

    game.run_game_give()

    decision_calls = []
    for client in clients.values():
        for call in client.calls:
            response_model = call["response_model"]
            if "target_name" in getattr(response_model, "model_fields", {}):
                decision_calls.append(call)

    assert len(decision_calls) == 3

    observed_choices = [
        set(get_args(call["response_model"].model_fields["target_name"].annotation))
        for call in decision_calls
    ]
    assert {"Bob", "Cara"} in observed_choices
    assert {"Alice", "Cara"} in observed_choices
    assert {"Alice", "Bob"} in observed_choices
