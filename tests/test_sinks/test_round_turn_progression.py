from types import SimpleNamespace

from core.gameboard import GameBoard
from core.sinks.game_sink import CapturingGameSink


class FakeGameMaster:
    def summariseRound(self, _game_board):
        return SimpleNamespace(round_summary="stub summary")


def test_new_round_emits_round_start_and_resets_turn_counter():
    sink = CapturingGameSink()
    board = GameBoard(game_master=FakeGameMaster(), game_sink=sink)

    board.add_agent_state("Ava", 2)
    board.add_agent_state("Bryn", 1)

    board.new_turn_print()
    board.new_turn_print()
    assert board.turn_number == 2

    board.newRound()

    assert board.round_number == 1
    assert board.turn_number == 0
    assert sink.round_summaries == ["stub summary"]
    assert sink.round_starts == [{"round_number": 1, "scores": {"Ava": 2, "Bryn": 1}}]
