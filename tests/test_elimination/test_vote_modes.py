from types import SimpleNamespace

import pytest

from tests.helpers.game_test_helpers import build_vote_game, host_messages, turn_payload


def test_run_voting_winner_chooses_selects_target_and_eliminates():
    game, board, agents, _clients = build_vote_game(
        {
            "Alice": [turn_payload(target_name="Bob")],
            "Bob": [],
            "Cara": [],
        }
    )
    alice = agents[0]
    eliminated = []

    game._validate_immunity = lambda immunity: []
    game.get_strategic_players = lambda _agents, top_player=True, limit=1: [alice]
    game.eliminate_player_by_name = lambda name: eliminated.append(name)

    game.run_voting_winner_chooses()

    expected = "Alice"
    assert expected in host_messages(board)[0]
    assert eliminated == ["Bob"]


def test_run_voting_winner_chooses_uses_real_strategy_selector():
    game, board, _agents, _clients = build_vote_game(
        {
            "Alice": [turn_payload(target_name="Bob")],
            "Bob": [],
            "Cara": [],
        },
        initial_scores={"Alice": 10, "Bob": 4, "Cara": 1},
    )
    eliminated = []

    game.eliminate_player_by_name = lambda name: eliminated.append(name)

    game.run_voting_winner_chooses()

    assert "Alice" in host_messages(board)[0]
    assert eliminated == ["Bob"]


def test_get_strategic_players_returns_top_players_with_limit():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": []},
        initial_scores={"Alice": 9, "Bob": 5, "Cara": 1},
    )

    selected = game.get_strategic_players(game.simulationEngine.agents, top_player=True, multiple=False)

    assert len(selected) == 1
    assert selected[0].name == "Alice"


def test_get_strategic_players_returns_bottom_players_with_limit():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": []},
        initial_scores={"Alice": 9, "Bob": 5, "Cara": 1},
    )

    selected = game.get_strategic_players(game.simulationEngine.agents, top_player=False, multiple=False)

    assert len(selected) == 1
    assert selected[0].name == "Cara"


def test_get_strategic_players_returns_none_for_empty_available_agents():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": []},
        initial_scores={"Alice": 9, "Bob": 1},
    )

    selected = game.get_strategic_players([], top_player=True, multiple=False)

    assert not selected #isEmpty


def test_get_strategic_players_returns_none_when_available_names_not_in_scores():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": []},
        initial_scores={"Alice": 9, "Bob": 1},
    )
    ghost = SimpleNamespace(name="Ghost")

    selected = game.get_strategic_players([ghost], top_player=True, multiple=False)

    assert not selected


def test_get_strategic_players_filters_to_available_agents_only():
    game, _board, agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": []},
        initial_scores={"Alice": 9, "Bob": 1, "Cara": 5},
    )
    available = [agent for agent in agents if agent.name in {"Bob", "Cara"}]

    selected = game.get_strategic_players(available, top_player=True, multiple=False)

    assert len(selected) == 1
    assert selected[0].name == "Cara"


def test_get_strategic_players_top_tie_applies_shuffle_then_limit(monkeypatch):
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": []},
        initial_scores={"Alice": 9, "Bob": 1, "Cara": 9},
    )

    monkeypatch.setattr(
        "gameplay_management.base_manager.random.shuffle",
        lambda names: names.reverse(),
    )

    selected = game.get_strategic_players(game.simulationEngine.agents, top_player=True, multiple=False)

    assert len(selected) == 1
    assert selected[0].name == "Cara"


def test_get_strategic_players_bottom_tie_returns_all_when_limit_exceeds_tie(monkeypatch):
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": []},
        initial_scores={"Alice": 1, "Bob": 1, "Cara": 9},
    )
    monkeypatch.setattr("gameplay_management.base_manager.random.shuffle", lambda _names: None)

    selected = game.get_strategic_players(game.simulationEngine.agents, top_player=False, multiple=True)

    assert len(selected) == 2
    assert {player.name for player in selected} == {"Alice", "Bob"}


def test_get_bottom_players_fills_from_next_lowest_scores():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": [], "Cara": []},
        initial_scores={"Alice": 1, "Bob": 2, "Cara": 3},
    )

    selected = game.get_bottom_players(game.simulationEngine.agents, min=2, multiple = False)

    assert [player.name for player in selected] == ["Alice", "Bob"]




def test_get_bottom_players_caps_at_available_players():
    game, _board, _agents, _clients = build_vote_game(
        {"Alice": [], "Bob": []},
        initial_scores={"Alice": 1, "Bob": 2},
    )

    selected = game.get_bottom_players(game.simulationEngine.agents, min=5)

    assert [player.name for player in selected] == ["Alice", "Bob"]




def test_run_voting_lowest_points_removed_announces_and_eliminates_lowest():
    game, board, agents, _clients = build_vote_game(
        {"Alice": [], "Bob": []},
        initial_scores={"Alice": 5, "Bob": 1},
    )
    bob = next(a for a in agents if a.name == "Bob")
    eliminated = []
    game.get_strategic_players = lambda _agents, top_player=False, limit=1: [bob]
    game.eliminate_player_by_name = lambda name: eliminated.append(name)

    game.run_voting_lowest_points_removed()

    assert "Bob" in host_messages(board)[0]
    assert eliminated == ["Bob"]


def test_run_voting_round_basic_dont_miss_forwards_to_basic_with_flag():
    game, _board, _agents, _clients = build_vote_game({})
    seen = []
    game.run_voting_round_basic = lambda immunity_players, dont_miss=False: seen.append(
        (immunity_players, dont_miss)
    )

    game.run_voting_round_basic_dont_miss(["Alice"])

    assert seen == [(["Alice"], True)]
