from types import SimpleNamespace

from gameplay_management.immunities.highest_points_immunity import HighestPointsImmunity
from gameplay_management.immunities.wildcard_immunity import WildcardImmunity


class _TrackingGameMaster:
    def __init__(self, chosen):
        self.chosen = chosen
        self.calls = []

    def choose_agent_based_on_parameter(self, board, names, trait):
        self.calls.append((board, list(names), trait))
        return SimpleNamespace(target_name=self.chosen, public_reason="chosen for chaos")


class _Board:
    def __init__(self, scores=None, names=None, gm=None):
        self.agent_scores = scores or {}
        self.agent_names = names or []
        self.game_master = gm
        self.host_messages = []

    def host_broadcast(self, message):
        self.host_messages.append(message)


def _engine(cfg=None, names=None):
    agents = [SimpleNamespace(name=name) for name in (names or [])]
    return SimpleNamespace(agents=agents, gameplay_config=cfg or SimpleNamespace(immunity_highest_points_only_one=False))


def test_highest_points_immunity_returns_all_tied_leaders_by_default():
    board = _Board(scores={"Alice": 5, "Bob": 7, "Cara": 7, "Dan": 1})
    game = HighestPointsImmunity(board, _engine(names=["Alice", "Bob", "Cara", "Dan"]))
    game.respond_to = lambda *_args, **_kwargs: SimpleNamespace(public_response="", private_thoughts="")
    game.publicPrivateResponse = lambda *_args, **_kwargs: None

    assert game.run_immunity() == ["Bob", "Cara"]


def test_highest_points_immunity_respects_cfg_only_one_on_tie(monkeypatch):
    board = _Board(scores={"Alice": 8, "Bob": 8, "Cara": 2})
    cfg = SimpleNamespace(immunity_highest_points_only_one=True)
    game = HighestPointsImmunity(board, _engine(cfg=cfg, names=["Alice", "Bob", "Cara"]))
    game.respond_to = lambda *_args, **_kwargs: SimpleNamespace(public_response="", private_thoughts="")
    game.publicPrivateResponse = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        "gameplay_management.immunities.highest_points_immunity.random.choice",
        lambda items: items[1],
    )

    assert game.run_immunity() == ["Bob"]


def test_highest_points_immunity_only_one_variant_forces_single_selection(monkeypatch):
    board = _Board(scores={"Alice": 8, "Bob": 8, "Cara": 2})
    cfg = SimpleNamespace(immunity_highest_points_only_one=False)
    game = HighestPointsImmunity(board, _engine(cfg=cfg, names=["Alice", "Bob", "Cara"]))
    game.respond_to = lambda *_args, **_kwargs: SimpleNamespace(public_response="", private_thoughts="")
    game.publicPrivateResponse = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        "gameplay_management.immunities.highest_points_immunity.random.choice",
        lambda items: items[0],
    )

    assert game._highest_points_immunity(True) == ["Alice"]


def test_wildcard_immunity_uses_chaotic_trait_and_returns_target():
    gm = _TrackingGameMaster("Cara")
    board = _Board(names=["Alice", "Bob", "Cara"], gm=gm)
    game = WildcardImmunity(board, _engine(names=["Alice", "Bob", "Cara"]))
    game.respond_to = lambda *_args, **_kwargs: SimpleNamespace(public_response="", private_thoughts="")
    game.publicPrivateResponse = lambda *_args, **_kwargs: None

    result = game.run_immunity()

    assert result == ["Cara"]
    assert gm.calls == [(board, ["Alice", "Bob", "Cara"], "chaotic")]
