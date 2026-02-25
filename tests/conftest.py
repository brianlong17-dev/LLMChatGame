import pytest
from unittest.mock import MagicMock

# ---------------------------------------------------------
# MOCK FIXTURES (The Dependencies)
# ---------------------------------------------------------

@pytest.fixture
def mock_game_board():
    """Returns a completely fake GameBoard."""
    return MagicMock()

@pytest.fixture
def mock_simulation_engine():
    """Returns a completely fake SimulationEngine."""
    return MagicMock()

@pytest.fixture
def mock_prompt_library(monkeypatch):
    """
    Patches the GamePromptLibrary constants so tests are deterministic.
    We use 'monkeypatch' (built-in pytest tool) instead of unittest.patch.
    """
    class MockLibrary:
        pd_split = 3
        pd_steal = 5
        pd_both_steal = 1
        
    # Apply the patch to the specific module where it's used
    # CHECK THIS PATH: Verify 'gameplay_management.game_mechanicsMixin' imports GamePromptLibrary
    monkeypatch.setattr("prompts.gamePrompts.GamePromptLibrary", MockLibrary)
    return MockLibrary

# ---------------------------------------------------------
# GAME INSTANCE FIXTURE (The Object Under Test)
# ---------------------------------------------------------
@pytest.fixture
def pd_game(mock_game_board, mock_simulation_engine):
    from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
    return GamePrisonersDilemma(mock_game_board, mock_simulation_engine)
