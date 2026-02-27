from types import SimpleNamespace
from typing import get_args

import pytest

from tests.helpers.game_test_helpers import (
    build_guess_game,
    host_messages,
    turn_payload,
)


@pytest.fixture(autouse=True)
def no_test_delays(monkeypatch):
    monkeypatch.setattr("gameplay_management.base_manager.time.sleep", lambda *_: None)


def test_guess_awards_points_to_all_correct_guessers(monkeypatch):
    game, board, _agents, clients = build_guess_game(
        {
            "Alice": [
                turn_payload(choice="2", public_response="Alice locks in 2"),
                turn_payload(public_response="Alice reacts"),
            ],
            "Bob": [
                turn_payload(choice="2", public_response="Bob picks 2"),
                turn_payload(public_response="Bob reacts"),
            ],
            "Cara": [
                turn_payload(choice="1", public_response="Cara goes with 1"),
                turn_payload(public_response="Cara reacts"),
            ],
        }
    )

    monkeypatch.setattr("gameplay_management.game_guess.random.randint", lambda _a, _b: 2)

    game.run_game_guess_the_number()

    assert board.agent_scores == {"Alice": 4, "Bob": 4, "Cara": 0}
    messages = host_messages(board)
    assert any("GUESS THE NUMBER" in m for m in messages)
    assert any("The number was... **2**" in m for m in messages)
    assert any("Alice, Bob guessed the number and each earn 4 points" in m for m in messages)
    for client in clients.values():
        client.assert_exhausted()


def test_guess_treats_non_numeric_and_out_of_range_as_invalid(monkeypatch):
    game, board, _agents, clients = build_guess_game(
        {
            "Alice": [
                turn_payload(choice="abc", public_response="Alice says letters"),
                turn_payload(public_response="Alice reacts"),
            ],
            "Bob": [
                turn_payload(choice="99", public_response="Bob says 99"),
                turn_payload(public_response="Bob reacts"),
            ],
        }
    )

    monkeypatch.setattr("gameplay_management.game_guess.random.randint", lambda _a, _b: 1)

    game.run_game_guess_the_number()

    assert board.agent_scores == {"Alice": 0, "Bob": 0}
    messages = host_messages(board)
    summary = next(m for m in messages if "Invalid guess from" in m)
    assert "Alice" in summary
    assert "Bob" in summary
    assert "guessed 99" not in summary
    for client in clients.values():
        client.assert_exhausted()


def test_guess_uses_constrained_choice_field_for_decisions(monkeypatch):
    game, _board, _agents, clients = build_guess_game(
        {
            "Alice": [
                turn_payload(choice="4"),
                turn_payload(public_response="Alice reacts"),
            ],
            "Bob": [
                turn_payload(choice="1"),
                turn_payload(public_response="Bob reacts"),
            ],
        }
    )

    monkeypatch.setattr("gameplay_management.game_guess.random.randint", lambda _a, _b: 3)

    game.run_game_guess_the_number()

    decision_calls = []
    for client in clients.values():
        for call in client.calls:
            if "choice" in getattr(call["response_model"], "model_fields", {}):
                decision_calls.append(call)

    assert len(decision_calls) == 2
    for call in decision_calls:
        choice_field = call["response_model"].model_fields["choice"]
        assert set(get_args(choice_field.annotation)) == {"1", "2", "3", "4"}


def test_guess_reaction_phase_calls_each_player_once(monkeypatch):
    game, _board, _agents, clients = build_guess_game(
        {
            "Alice": [
                turn_payload(choice="2"),
                turn_payload(public_response="Alice reaction"),
            ],
            "Bob": [
                turn_payload(choice="1"),
                turn_payload(public_response="Bob reaction"),
            ],
            "Cara": [
                turn_payload(choice="4"),
                turn_payload(public_response="Cara reaction"),
            ],
        }
    )

    monkeypatch.setattr("gameplay_management.game_guess.random.randint", lambda _a, _b: 4)

    game.run_game_guess_the_number()

    assert len(clients["Alice"].calls) == 2
    assert len(clients["Bob"].calls) == 2
    assert len(clients["Cara"].calls) == 2
    for client in clients.values():
        client.assert_exhausted()


def test_build_result_string_handles_empty_case():
    game, _board, _agents, _clients = build_guess_game({"Solo": []})
    assert game._build_guess_the_number_result_string([], [], [], 4) == "No valid guesses this round."


def test_build_result_string_mixed_groups():
    game, _board, _agents, _clients = build_guess_game({"Stub": []})
    correct = [SimpleNamespace(name="Alice")]
    incorrect = [(SimpleNamespace(name="Bob"), 3)]
    invalid = [SimpleNamespace(name="Cara")]

    text = game._build_guess_the_number_result_string(correct, incorrect, invalid, 4)

    assert "Alice guessed the number and each earn 4 points" in text
    assert "Bob (guessed 3) missed the mark" in text
    assert "Invalid guess from: Cara" in text


@pytest.mark.xfail(
    strict=True,
    reason="GameGuess still hardcodes number_range=4; future behavior should read phase_factory config.",
)
def test_guess_reads_number_range_from_phase_factory_when_available(monkeypatch):
    game, board, _agents, _clients = build_guess_game(
        {
            "Alice": [
                turn_payload(choice="7", public_response="Alice picks 7"),
                turn_payload(public_response="Alice reacts"),
            ],
            "Bob": [
                turn_payload(choice="1", public_response="Bob picks 1"),
                turn_payload(public_response="Bob reacts"),
            ],
        }
    )

    # Future intent: game should read this value instead of a hardcoded range.
    board.phase_factory = SimpleNamespace(number_range_for_guessing=7)
    monkeypatch.setattr("gameplay_management.game_guess.random.randint", lambda _a, _b: 7)

    game.run_game_guess_the_number()

    assert board.agent_scores == {"Alice": 7, "Bob": 0}
