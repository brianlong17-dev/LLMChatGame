from tests.helpers.game_test_helpers import (
    build_targeted_choice_game,
    host_messages,
    turn_payload,
)


def test_run_game_steal_standard_workflow_takes_full_prompt_points(monkeypatch):
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Alice": [
                turn_payload(target_name="Bob"),
                turn_payload(public_response="Alice reaction"),
            ],
            "Bob": [
                turn_payload(public_response="Bob reaction"),
                turn_payload(target_name="Alice"),
            ],
        },
        initial_scores={"Alice": 10, "Bob": 10},
    )

    monkeypatch.setattr("gameplay_management.game_targeted_choice.GamePromptLibrary.targeted_games_points", 4)
    game.run_game_steal()

    assert board.agent_scores == {"Alice": 10, "Bob": 10}
    msgs = host_messages(board)
    assert any("Alice steals from Bob" in m for m in msgs)
    assert any("Bob steals from Alice" in m for m in msgs)
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_run_game_steal_handles_partial_and_zero_point_steals():
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Bob": [
                turn_payload(target_name="Alice"),
                turn_payload(public_response="Bob reaction to empty pockets"),
                turn_payload(public_response="Bob reaction to losing points"),
            ],
            "Alice": [
                turn_payload(target_name="Bob"),
            ],
        },
        initial_scores={"Alice": 0, "Bob": 2},
    )

    game.run_game_steal()

    assert board.agent_scores == {"Alice": 2, "Bob": 0}
    msgs = host_messages(board)
    assert any("empty pockets" in m for m in msgs)
    assert any("gains 2 points" in m for m in msgs)
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_run_game_sacrifice_malformed_target():
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Alice": [
                turn_payload(target_name="Bob", points_to_spend=2),
            ],
            "Bob": [
                turn_payload(public_response="Bob reacts to Alice attack"),
                turn_payload(target_name="XXX", points_to_spend=2),
                turn_payload(public_response="Bob reacts to invalid move"),
            ],
        },
        initial_scores={"Alice": 3, "Bob": 10},
    )

    game.run_game_sacrifice_points()

    assert board.agent_scores == {"Alice": 1, "Bob": 8}
    assert any("invalid target" in m for m in host_messages(board))
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_run_game_sacrifice_invalid_target_with_positive_spend_is_noop():
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Alice": [
                turn_payload(target_name="XXX", points_to_spend=3),
                turn_payload(public_response="Alice reacts to invalid"),
            ],
            "Bob": [
                turn_payload(target_name="Pass", points_to_spend=0),
                turn_payload(public_response="Bob reacts to pass"),
            ],
        },
        initial_scores={"Alice": 7, "Bob": 10},
    )

    game.run_game_sacrifice_points()

    assert board.agent_scores == {"Alice": 7, "Bob": 10}
    msgs = host_messages(board)
    assert any("invalid target" in m for m in msgs)
    assert any("passes" in m for m in msgs)
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_run_game_sacrifice_clamps_spend_and_handles_pass():
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Alice": [
                turn_payload(target_name="Bob", points_to_spend=9),
            ],
            "Bob": [
                turn_payload(public_response="Bob reacts to attack"),
                turn_payload(target_name="Pass", points_to_spend=0),
                turn_payload(public_response="Bob reacts to pass"),
            ],
        },
        initial_scores={"Alice": 3, "Bob": 10},
    )

    game.run_game_sacrifice_points()

    assert board.agent_scores == {"Alice": 0, "Bob": 7}
    msgs = host_messages(board)
    assert any("sacrifices 3" in m for m in msgs)
    assert any("passes" in m for m in msgs)
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()


def test_run_game_sacrifice_edge_cases():
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Alice": [turn_payload(target_name="Bob", points_to_spend=999)],
            "Bob": [
                turn_payload(public_response="Bob reacts to Alice attack"),
                turn_payload(target_name="Cara", points_to_spend=-2),
                turn_payload(public_response="Bob reacts to pass"),
            ],
            "Cara": [
                turn_payload(target_name="Pass", points_to_spend=4),
                turn_payload(public_response="Cara reacts to pass"),
            ],
            "Dan": [
                turn_payload(target_name="Pass???", points_to_spend=0),
                turn_payload(public_response="Dan reacts to invalid/pass"),
            ],
        },
        initial_scores={"Alice": 3, "Bob": 10, "Cara": 5, "Dan": 7},
    )

    game.run_game_sacrifice_points()

    assert board.agent_scores == {"Alice": 0, "Bob": 7, "Cara": 5, "Dan": 7}
    msgs = host_messages(board)
    assert any("sacrifices 3" in m for m in msgs)
    assert sum("passes" in m for m in msgs) >= 3
    for client in clients.values():
        client.assert_exhausted()


def test_run_game_sacrifice_zero_points_skips_turn_and_goes_to_reaction():
    game, board, _agents, clients = build_targeted_choice_game(
        {
            "Alice": [
                turn_payload(public_response="Alice reacts to no-points message"),
            ],
            "Bob": [
                turn_payload(target_name="Pass", points_to_spend=0),
                turn_payload(public_response="Bob reacts to pass"),
            ],
        },
        initial_scores={"Alice": 0, "Bob": 5},
    )

    game.run_game_sacrifice_points()

    assert board.agent_scores == {"Alice": 0, "Bob": 5}
    msgs = host_messages(board)
    assert any("has no points" in m for m in msgs)
    clients["Alice"].assert_exhausted()
    clients["Bob"].assert_exhausted()
