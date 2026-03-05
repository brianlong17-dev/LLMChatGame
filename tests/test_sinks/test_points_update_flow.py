from types import SimpleNamespace

from core.gameboard import GameBoard
from core.sinks.game_sink import CapturingGameSink


class FakeGameMaster:
    def summariseRound(self, _game_board):
        return SimpleNamespace(round_summary="stub")


def test_append_agent_points_emits_score_snapshot():
    sink = CapturingGameSink()
    board = GameBoard(game_master=FakeGameMaster(), game_sink=sink)

    board.add_agent_state("Ava", 1)
    board.add_agent_state("Bryn", 0)

    board.append_agent_points("Ava", 2)

    assert board.agent_scores == {"Ava": 3, "Bryn": 0}
    assert sink.points_updates[-1] == {"Ava": 3, "Bryn": 0}


def test_reset_scores_emits_score_snapshot():
    sink = CapturingGameSink()
    board = GameBoard(game_master=FakeGameMaster(), game_sink=sink)

    board.add_agent_state("Ava", 4)
    board.add_agent_state("Bryn", 2)

    board.resetScores()

    assert board.agent_scores == {"Ava": 0, "Bryn": 0}
    assert sink.points_updates[-1] == {"Ava": 0, "Bryn": 0}
