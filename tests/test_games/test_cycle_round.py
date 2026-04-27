import pytest

from gameplay_management.game_cycle.game_knives import _PlayerState
from tests.helpers.game_test_helpers import (
    build_knives_game,
    turn_payload,
)


# ──────────────────────────────────────────────
# Group 1: Context Compression
# ──────────────────────────────────────────────

def _build_compression_game(agent_specs, full_context_cycles=2, initial_scores=None):
    return build_knives_game(
        agent_specs,
        initial_scores=initial_scores,
        config_overrides={
            "cycle_use_context_compression": True,
            "cycle_use_optional_response": False,
            "cycle_full_context_cycles": full_context_cycles,
            "cycle_buffer_amount": 0.4,
        },
    )


def test_compress_round_produces_summary_entry():
    """After one compress call, summaries list has an entry and watermark advances."""
    game, board, agents, clients = _build_compression_game({
        "Alice": [],
        "Bob": [],
        "Cara": [],
    })
    game._cycle_game_setup()
    initial_watermark = game._message_unsumarised_after

    # Broadcast some messages to have something to compress
    board.host_broadcast("test message 1")
    board.host_broadcast("test message 2")

    game._compress_round()

    assert len(game.summaries) == 1
    assert game.summaries[0][0] == "[test summary]"
    assert game._message_unsumarised_after > initial_watermark


def test_push_summaries_respects_full_context_cycles():
    """With full_context_cycles=2, first 2 rounds don't push; round 3 does."""
    game, board, agents, clients = _build_compression_game({
        "Alice": [],
        "Bob": [],
    }, full_context_cycles=2)
    game._cycle_game_setup()

    # Simulate 3 rounds of messages + compression
    for i in range(3):
        board.host_broadcast(f"round {i+1} message")
        game._compress_round()

    # After 3 compressions with window=2, the first summary should be pushed
    assert board._current_round_summarisation is not None
    assert "Cycle 1 summary" in board._current_round_summarisation


def test_no_compression_when_disabled():
    """With compression off, _compress_round is a no-op."""
    game, board, agents, clients = build_knives_game(
        {"Alice": [], "Bob": []},
        config_overrides={
            "cycle_use_context_compression": False,
            "cycle_use_optional_response": False,
        },
    )
    game._cycle_game_setup()

    board.host_broadcast("some message")
    game._compress_round()  # should be a no-op

    assert not hasattr(game, "summaries")
    assert not board._current_round_summarisation


# ──────────────────────────────────────────────
# Group 2: Optional Response Buffer
# ──────────────────────────────────────────────

def _build_optional_game(agent_specs, buffer_amount=0.4, initial_scores=None):
    return build_knives_game(
        agent_specs,
        initial_scores=initial_scores,
        config_overrides={
            "cycle_use_context_compression": False,
            "cycle_use_optional_response": True,
            "cycle_buffer_amount": buffer_amount,
        },
    )


def test_buffer_starts_at_zero_first_turn_skipped():
    """With buffer=0, optional turn is skipped — no API call consumed."""
    game, board, agents, clients = _build_optional_game({
        "Alice": [],  # no queued responses needed — turn should be skipped
    })
    game._cycle_game_setup()
    agents[0].optional_response_buffer = 0

    game._optional_pitch([_PlayerState(agent=a) for a in agents])

    assert len(clients["Alice"].calls) == 0


def test_buffer_accumulates_and_allows_response():
    """After enough buffer accumulation, an optional turn runs and broadcasts."""
    game, board, agents, clients = _build_optional_game({
        "Alice": [
            # Third call will actually run — needs a response
            turn_payload(public_response="I have something to say"),
        ],
    }, buffer_amount=0.4)
    game._cycle_game_setup()
    agents[0].optional_response_buffer = 0
    wrapped = [_PlayerState(agent=agents[0])]

    # First two calls: buffer too low (0 + 0.4 = 0.4, 0.4 + 0.4 = 0.8)
    game._optional_pitch(wrapped)
    game._optional_pitch(wrapped)
    assert len(clients["Alice"].calls) == 0

    # Third call: buffer = 0.8 + 0.4 = 1.2 >= 1.0, turn runs
    game._optional_pitch(wrapped)
    assert len(clients["Alice"].calls) == 1
    # Buffer should be 1.2 - 1.0 = 0.2
    assert agents[0].optional_response_buffer == pytest.approx(0.2)


def test_silent_optional_turn_preserves_buffer():
    """If agent stays silent on optional turn, buffer is not deducted."""
    game, board, agents, clients = _build_optional_game({
        "Alice": [
            turn_payload(public_response=""),  # stays silent
        ],
    }, buffer_amount=0.4)
    game._cycle_game_setup()
    agents[0].optional_response_buffer = 1.0

    game._optional_pitch([_PlayerState(agent=agents[0])])

    assert len(clients["Alice"].calls) == 1
    # Buffer should be 1.0 + 0.4 = 1.4 (earned buffer, no deduction for silence)
    assert agents[0].optional_response_buffer == pytest.approx(1.4)


def test_optional_response_flag_set_on_setup():
    """Setup turns on the flag on the round's turn manager."""
    game, board, agents, clients = _build_optional_game({"Alice": []})

    game._cycle_game_setup()
    assert game.turn_manager.optional_responses_in_use is True


# ──────────────────────────────────────────────
# Group 3: GameKnives Integration
# ──────────────────────────────────────────────

def _build_simple_knives(agent_specs, initial_scores=None):
    """No compression, no optional responses — minimal queue requirements."""
    return build_knives_game(
        agent_specs,
        initial_scores=initial_scores,
        config_overrides={
            "cycle_use_context_compression": False,
            "cycle_use_optional_response": False,
        },
    )


def test_knives_full_game_3_players_one_round_kill():
    """Alice stabs Bob, Bob stabs Alice, Cara stabs Bob. Bob dies (2 stabs).
    Alice survives with 1 stab (runner-up), gets 1 bonus point + reaction turn.
    Round 2: knife redistribution gives Alice 2 knives, Cara 1.
    Both stab each other equally → all-die scenario → game ends."""
    game, board, agents, clients = _build_simple_knives(
        {
            # Round 1: each player makes a choice
            "Alice": [turn_payload(knife_1="Bob")],
            "Bob": [turn_payload(knife_1="Alice")],
            "Cara": [turn_payload(knife_1="Bob")],
        },
    )

    # After round 1: Bob dies with 2 stabs (Alice has 1, Cara has 0)
    # Alice is runner-up with 1 stab → gets 1 bonus point + reaction turn
    # Knife redistribution: Alice gets 2 total (1 from stab + 1 from Bob), Cara gets 1

    # Update queues to include round 2 + runner-up reaction
    clients["Alice"]._responses.extend([
        # runner-up reaction turn (round 1)
        {"public_response": "I survived!", "private_thoughts": "close call"},
        # round 2 knife choice (Alice has 2 knives: stab Cara once, pass on 2nd)
        {"knife_1": "Cara", "knife_2": "Pass", "public_response": "", "private_thoughts": ""},
    ])
    clients["Cara"]._responses.extend([
        # round 2 knife choice (Cara has 1 knife: stab Alice)
        {"knife_1": "Alice", "public_response": "", "private_thoughts": ""},
    ])

    game.run_game()

    # Bob got 0 points (died round 1)
    # Alice got 1 point (runner-up bonus round 1), then died round 2 with equal stabs → no additional points
    # Cara also died round 2
    assert board.agent_scores["Bob"] == 0
    assert board.agent_scores["Alice"] == 1


def test_knives_all_die_simultaneously_ends_game():
    """All 3 players stab each other (1 stab each) → all die → game ends cleanly."""
    game, board, agents, clients = _build_simple_knives(
        {
            "Alice": [turn_payload(knife_1="Bob")],
            "Bob": [turn_payload(knife_1="Cara")],
            "Cara": [turn_payload(knife_1="Alice")],
        },
    )

    game.run_game()

    # All died simultaneously — no survivor bonus, no crash
    assert board.agent_scores["Alice"] == 0
    assert board.agent_scores["Bob"] == 0
    assert board.agent_scores["Cara"] == 0


def test_knives_everyone_passes_then_stabs():
    """Round 1: all pass (0 stabs, no one dies). Round 2: circular stabs → all die simultaneously.
    Alice stabs Bob, Bob stabs Cara, Cara stabs Alice (each gets 1 stab, max=1, all die)."""
    game, board, agents, clients = _build_simple_knives(
        {
            "Alice": [
                turn_payload(knife_1="Pass"),          # round 1: pass
                turn_payload(knife_1="Bob"),            # round 2: stab Bob
            ],
            "Bob": [
                turn_payload(knife_1="Pass"),           # round 1: pass
                turn_payload(knife_1="Cara"),           # round 2: stab Cara
            ],
            "Cara": [
                turn_payload(knife_1="Pass"),           # round 1: pass
                turn_payload(knife_1="Alice"),          # round 2: stab Alice
            ],
        },
    )

    game.run_game()

    # Game should complete without crashing on the all-pass round
    # Round 1: all pass → no one dies (all have 0 stabs)
    # Round 2: Alice(1)→Bob, Bob(1)→Cara, Cara(1)→Alice → all die with 1 stab each (all-die scenario)
    assert board.agent_scores["Bob"] == 0
    assert board.agent_scores["Alice"] == 0
    assert board.agent_scores["Cara"] == 0
