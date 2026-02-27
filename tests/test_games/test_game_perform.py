import importlib
import inspect
from types import SimpleNamespace

import pytest

from agents.player import Debater
from core.gameboard import GameBoard
from tests.helpers.game_test_helpers import QueuedClient, host_messages, turn_payload


@pytest.fixture(autouse=True)
def no_test_delays(monkeypatch):
    monkeypatch.setattr("gameplay_management.base_manager.time.sleep", lambda *_: None)


class NoopGameMaster:
    pass


def _load_game_perform_class():
    try:
        module = importlib.import_module("gameplay_management.game_perform")
    except Exception as exc:
        pytest.fail(f"GamePerform is not importable yet: {exc}")
    return module.GamePerformSobStory


def _build_perform_game(agent_specs, initial_scores=None):
    game_cls = _load_game_perform_class()
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [
        Debater(
            name=name,
            initial_persona=f"{name} persona",
            initial_form=f"{name} form",
            client=clients[name],
            model_name="test-model",
            higher_model_name="test-model-high",
            speaking_style="normal",
        )
        for name in agent_specs
    ]

    board = GameBoard(NoopGameMaster())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = SimpleNamespace(agents=agents)
    game = game_cls(board, simulation)
    game._shuffled_agents = lambda: list(simulation.agents)
    return game, board, agents, clients


def _run_sob_story(game, board):
    bound = game.run_game_sob_story
    params = inspect.signature(bound).parameters
    if len(params) == 0:
        return bound()
    return bound(board)


def _default_three_player_script():
    return {
        "Alice": [
            turn_payload(story_text="Alice sob story", public_response="Alice story"),
            turn_payload(score="7", public_response="Alice rates Bob", private_thoughts="A->B"),
            turn_payload(score="8", public_response="Alice rates Cara", private_thoughts="A->C"),
            turn_payload(
                public_response="Alice reacts to score summary",
                private_thoughts="Alice reaction thoughts",
            ),
        ],
        "Bob": [
            turn_payload(story_text="Bob sob story", public_response="Bob story"),
            turn_payload(score="9", public_response="Bob rates Alice", private_thoughts="B->A"),
            turn_payload(score="5", public_response="Bob rates Cara", private_thoughts="B->C"),
            turn_payload(
                public_response="Bob reacts to score summary",
                private_thoughts="Bob reaction thoughts",
            ),
        ],
        "Cara": [
            turn_payload(story_text="Cara sob story", public_response="Cara story"),
            turn_payload(score="6", public_response="Cara rates Alice", private_thoughts="C->A"),
            turn_payload(score="4", public_response="Cara rates Bob", private_thoughts="C->B"),
            turn_payload(
                public_response="Cara reacts to score summary",
                private_thoughts="Cara reaction thoughts",
            ),
        ],
    }


def test_sob_story_broadcasts_game_intro_once():
    game, board, _agents, _clients = _build_perform_game(_default_three_player_script())

    _run_sob_story(game, board)

    messages = host_messages(board)
    intro_msgs = [m for m in messages if "Every reality contestant has one" in m]
    assert len(intro_msgs) == 1


def test_sob_story_uses_higher_model_for_story_turn_only():
    game, board, _agents, clients = _build_perform_game(_default_three_player_script())

    _run_sob_story(game, board)

    for name, client in clients.items():
        assert len(client.calls) == 4
        assert client.calls[0]["model"] == "test-model-high", f"{name} story turn should use higher model"
        assert client.calls[1]["model"] == "test-model"
        assert client.calls[2]["model"] == "test-model"
        assert client.calls[3]["model"] == "test-model"


def test_sob_story_makes_one_performer_followup_call_with_score_summary():
    game, board, _agents, clients = _build_perform_game(_default_three_player_script())

    _run_sob_story(game, board)

    for name, client in clients.items():
        follow_up_user_prompt = client.calls[3]["messages"][-1]["content"]
        assert f"Scores for {name}" in follow_up_user_prompt


def test_sob_story_each_story_gets_scored_by_all_other_players():
    game, board, _agents, clients = _build_perform_game(_default_three_player_script())

    _run_sob_story(game, board)

    # 3 players => each should act once as storyteller, twice as judge, and once to react to their score summary.
    for client in clients.values():
        assert len(client.calls) == 4

    # Total judgments expected: 3 storytellers * 2 judges each.
    public_msgs = [entry for entry in board.currentRound if entry["speaker"] != "HOST"]
    assert len(public_msgs) >= 6


def test_sob_story_appends_total_points_from_received_scores():
    game, board, _agents, _clients = _build_perform_game(_default_three_player_script())

    _run_sob_story(game, board)

    # Current game logic appends rounded average score per performance.
    assert board.agent_scores["Alice"] == 8  # round((9 + 6) / 2)
    assert board.agent_scores["Bob"] == 6  # round((8 + 4) / 2)
    assert board.agent_scores["Cara"] == 5  # round((5 + 5) / 2)


def test_sob_story_ignores_invalid_scores():
    game, board, _agents, _clients = _build_perform_game(
        {
            "Alice": [
                turn_payload(story_text="Alice story", public_response="Alice story"),
                turn_payload(score="11", public_response="Alice rates Bob", private_thoughts="too high"),
                turn_payload(public_response="Alice reacts", private_thoughts="Alice reacts"),
            ],
            "Bob": [
                turn_payload(story_text="Bob story", public_response="Bob story"),
                turn_payload(score="cat", public_response="Bob rates Alice", private_thoughts="not numeric"),
                turn_payload(public_response="Bob reacts", private_thoughts="Bob reacts"),
            ],
        }
    )

    _run_sob_story(game, board)

    # Non-numeric or missing score fields fall back to 5.
    assert board.agent_scores["Alice"] == 5
    assert board.agent_scores["Bob"] == 5


def test_sob_story_keeps_out_of_range_numeric_scores_as_is():
    game, board, _agents, _clients = _build_perform_game(
        {
            "Alice": [
                turn_payload(story_text="Alice story", public_response="Alice story"),
                turn_payload(public_response="Alice reacts", private_thoughts="Alice reacts"),
                turn_payload(score="0", public_response="Alice rates Bob", private_thoughts="zero"),
            ],
            "Bob": [
                turn_payload(story_text="Bob story", public_response="Bob story"),
                turn_payload(score="11", public_response="Bob rates Alice", private_thoughts="too high"),
                turn_payload(public_response="Bob reacts", private_thoughts="Bob reacts"),
            ],
        }
    )

    _run_sob_story(game, board)

    assert board.agent_scores["Alice"] == 11
    assert board.agent_scores["Bob"] == 0
