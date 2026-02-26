from types import SimpleNamespace

from core.gameboard import GameBoard
from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
from tests.helpers.game_test_helpers import NoopGameMaster


def test_prisoners_dilemma_split_vs_steal():
    game = GamePrisonersDilemma(GameBoard(NoopGameMaster()), SimpleNamespace(agents=[]))
    p0, p1, _ = game._calculate_pd_payout("split", "steal", "A", "B")
    assert (p0, p1) == (0, 5)
