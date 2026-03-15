from types import SimpleNamespace

from gameplay_management.immunities.highest_points_immunity import HighestPointsImmunity
from gameplay_management.immunities.wildcard_immunity import WildcardImmunity


class _TrackingGameMaster:
    def __init__(self, chosen):
        self.chosen = chosen
        self.calls = []

    def choose_agent_based_on_parameter(self, board, names, trait):
        self.calls.append((board, list(names), trait))
        return SimpleNamespace(target_name=self.chosen, public_reason="because")


class _Board:
    def __init__(self, scores=None, names=None, gm=None):
        self.agent_scores = scores or {}
        self._agent_names = names or []
        self.game_master = gm
        self.host_messages = []

    def agent_names(self):
        return list(self._agent_names)

    def host_broadcast(self, message):
        self.host_messages.append(message)


def _sim(names):
    return SimpleNamespace(
        agents=[SimpleNamespace(name=name) for name in names],
        gameplay_config=SimpleNamespace(immunity_highest_points_only_one=False),
        game_master=None,
    )


def test_get_highest_points_players_immunity_returns_all_tied_leaders():
    game_board = _Board(scores={"Alice": 5, "Bob": 7, "Cara": 7, "Dan": 1})
    game = HighestPointsImmunity(game_board, _sim(["Alice", "Bob", "Cara", "Dan"]))
    game.respond_to = lambda *_args, **_kwargs: None
    game.publicPrivateResponse = lambda *_args, **_kwargs: None
    assert game._highest_points_immunity() == ["Bob", "Cara"]


def test_get_highest_points_players_immunity_only_one_selects_single_on_tie(monkeypatch):
    game_board = _Board(scores={"Alice": 8, "Bob": 8, "Cara": 2})
    game = HighestPointsImmunity(game_board, _sim(["Alice", "Bob", "Cara"]))
    game.respond_to = lambda *_args, **_kwargs: None
    game.publicPrivateResponse = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        "gameplay_management.immunities.highest_points_immunity.random.choice",
        lambda items: items[1],
    )
    assert game._highest_points_immunity(only_one=True) == ["Bob"]


def test_get_wildcard_player_immunity_queries_chaotic_trait_and_returns_target():
    gm = _TrackingGameMaster("Cara")
    game_board = _Board(names=["Alice", "Bob", "Cara"], gm=gm)
    simulation = _sim(["Alice", "Bob", "Cara"])
    simulation.game_master = gm
    game = WildcardImmunity(game_board, simulation)
    game.respond_to = lambda *_args, **_kwargs: None
    game.publicPrivateResponse = lambda *_args, **_kwargs: None

    result = game.run_immunity()

    assert result == ["Cara"]
    assert gm.calls == [(game_board, ["Alice", "Bob", "Cara"], "The most CHAOTIC player is the one that has the most unpredictable actions, and causes the most disruption to the other players. They are the wild card, and can be both a threat and an asset to the other players. They are often the most entertaining to watch, but also the most difficult to predict.")]


def test_get_wildcard_player_random_trait_uses_selected_trait(monkeypatch):
    gm = _TrackingGameMaster("Alice")
    game_board = _Board(names=["Alice", "Bob"], gm=gm)
    simulation = _sim(["Alice", "Bob"])
    simulation.game_master = gm
    game = WildcardImmunity(game_board, simulation)

    monkeypatch.setattr(
        "gameplay_management.immunities.wildcard_immunity.random.choice",
        lambda items: "calculating",
    )
    result = game.get_wildcard_player_random_trait()

    assert result == ["Alice"]
    assert gm.calls == [(game_board, ["Alice", "Bob"], "calculating")]
