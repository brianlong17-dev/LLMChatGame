import pytest
from unittest.mock import MagicMock
# Import your actual classes here
from core.gameboard import GameBoard
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from agents.player import Debater
from prompts.gamePrompts import GamePromptLibrary

def test_prisoners_dilemma_split_vs_steal():
    