from types import SimpleNamespace

from core.game_config import GameConfig
from core.gameboard import GameBoard
from gameplay_management.games.game_prisoners_dilemma import GamePrisonersDilemma
from tests.helpers.game_test_helpers import TestGameSink, TestSimulation, attach_test_runtime


def test_prisoners_dilemma_split_vs_steal():
    board = GameBoard(TestGameSink())
    simulation = TestSimulation([], gameplay_config=GameConfig())
    game = GamePrisonersDilemma(board, simulation)
    attach_test_runtime(board, simulation, game)
    p0, p1, _ = game._calculate_pd_payout("split", "steal", "A", "B")
    assert (p0, p1) == (0, 5)
