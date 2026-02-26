from types import SimpleNamespace

from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin


class _TrackingGameMaster:
    def __init__(self, chosen):
        self.chosen = chosen
        self.calls = []

    def choose_agent_based_on_parameter(self, board, names, trait):
        self.calls.append((board, list(names), trait))
        return SimpleNamespace(target_name=self.chosen)


class _Board:
    def __init__(self, scores=None, names=None, gm=None):
        self.agent_scores = scores or {}
        self.agent_names = names or []
        self.game_master = gm


def test_get_highest_points_players_immunity_returns_all_tied_leaders():
    game_board = _Board(scores={"Alice": 5, "Bob": 7, "Cara": 7, "Dan": 1})
    game = ImmunityMechanicsMixin(game_board, SimpleNamespace(agents=[]))
    assert game.get_highest_points_players_immunity() == ["Bob", "Cara"]


def test_get_highest_points_players_immunity_only_one_selects_single_on_tie(monkeypatch):
    game_board = _Board(scores={"Alice": 8, "Bob": 8, "Cara": 2})
    game = ImmunityMechanicsMixin(game_board, SimpleNamespace(agents=[]))

    monkeypatch.setattr(
        "gameplay_management.immunity_mechanicsMixin.random.choice",
        lambda items: items[1],
    )
    assert game.get_highest_points_players_immunity_only_one() == ["Bob"]


def test_get_wildcard_player_immunity_queries_chaotic_trait_and_returns_target():
    gm = _TrackingGameMaster("Cara")
    game_board = _Board(names=["Alice", "Bob", "Cara"], gm=gm)
    game = ImmunityMechanicsMixin(game_board, SimpleNamespace(agents=[]))

    result = game.get_wildcard_player_immunity()

    assert result == ["Cara"]
    assert gm.calls == [(game_board, ["Alice", "Bob", "Cara"], "chaotic")]


def test_get_wildcard_player_random_trait_uses_selected_trait(monkeypatch):
    gm = _TrackingGameMaster("Alice")
    game_board = _Board(names=["Alice", "Bob"], gm=gm)
    game = ImmunityMechanicsMixin(game_board, SimpleNamespace(agents=[]))

    monkeypatch.setattr(
        "gameplay_management.immunity_mechanicsMixin.random.choice",
        lambda items: "calculating",
    )
    result = game.get_wildcard_player_random_trait()

    assert result == ["Alice"]
    assert gm.calls == [(game_board, ["Alice", "Bob"], "calculating")]
