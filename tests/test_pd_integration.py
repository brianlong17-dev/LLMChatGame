import pytest
from unittest.mock import MagicMock
from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
from agents.player import Debater
from core.simulation_engine import SimulationEngine

# --- FIXTURES ---

@pytest.fixture
def real_agent_hero():
    """A real Agent with a mocked client."""
    mock_client = MagicMock()
    # Mocking the 'create' method early so it's ready
    agent = Debater(
        name="Hero", 
        client=mock_client, 
        model_name="gpt-4o", 
        initial_persona="I am a hero.",
        initial_form="Human",
        speaking_style="normal" # Uncomment if your class requires this
    )
    return agent

@pytest.fixture
def real_agent_villain():
    """A second real Agent."""
    mock_client = MagicMock()
    agent = Debater(
        name="Villain", 
        client=mock_client, 
        model_name="gpt-4o",
        initial_persona="I am a villain.",
        initial_form="Human",
        speaking_style="normal" 
    )
    return agent

@pytest.fixture
def integration_game():
    """
    Creates the Game Manager linked to a real Simulation Engine.
    We don't pass a board in; we let the engine create it.
    """
    engine = SimulationEngine() 
    
    # We grab the board the engine created automatically
    game = GamePrisonersDilemma(engine.gameBoard, engine)
    
    return game

# --- THE TEST ---

def test_full_pd_round_execution(integration_game, real_agent_hero, real_agent_villain):
    """
    Tests the entire flow: 
    Prompt Generation -> 'LLM' Response -> Parsing -> Scoring -> Broadcasting.
    """
    
    # 1. SETUP: Create the "Brain" Responses (The Mock Objects)
    # ---------------------------------------------------------
    # Hero decides to SPLIT
    hero_decision = MagicMock()
    hero_decision.action = "split"
    hero_decision.public_response = "I trust you, let's split."
    hero_decision.mathematicalAssessment = "Splitting maximizes group points."
    # Add other required fields if your Pydantic model demands them
    
    # Villain decides to STEAL
    villain_decision = MagicMock()
    villain_decision.action = "steal"
    villain_decision.public_response = "Of course I will split!"
    villain_decision.mathematicalAssessment = "Stealing gives me 5."

    # 2. SETUP: Inject the Brains into the Agents
    # ---------------------------------------------------------
    # When agent.client.create(...) is called, return our fake decision object
    real_agent_hero.client.create.return_value = hero_decision
    real_agent_villain.client.create.return_value = villain_decision
    
    # 3. SETUP: Initialize the Engine State
    # ---------------------------------------------------------
    # Add agents to the engine
    integration_game.simulationEngine.agents = [real_agent_hero, real_agent_villain]
    
    # Initialize the board (Create score dicts, etc.)
    # This must happen AFTER adding agents so they get entry in the scoreboard
    integration_game.simulationEngine.initialiseGameBoard()
    
    # Verify start state (Optional but good sanity check)
    assert integration_game.simulationEngine.gameBoard.agent_scores["Hero"] == 0
    
    # 4. ACT: Run the Game Round
    # ---------------------------------------------------------
    # This runs the threads, calls the mocks, calculates math, updates board
    integration_game.run_game_prisoners_dilemma(choose_partner=False)

    # 5. ASSERT: Verify Logic
    # ---------------------------------------------------------
    board = integration_game.simulationEngine.gameBoard
    
    hero_score = board.agent_scores["Hero"]
    villain_score = board.agent_scores["Villain"]

    # Logic: Hero Split (0) vs Villain Steal (5)
    assert hero_score == 0, f"Hero expected 0, got {hero_score}"
    assert villain_score == 5, f"Villain expected 5, got {villain_score}"

    # 6. ASSERT: Verify Narrative Logs
    # ---------------------------------------------------------
    # Depending on how your GameBoard stores history (Strings or Dicts), adjust this:
    history = board.currentRound
    
    # Debug print if assertion fails
    print("DEBUG HISTORY:", history) 

    # If history is a list of strings:
    # match_found = any("STOLE from Hero" in event for event in history)
    
    # If history is a list of dicts (e.g. {'role': 'host', 'message': '...'}):
    match_found = any(
        "STOLE from Hero" in str(event) # str(event) catches both dict values and raw strings
        for event in history
    )
    
    assert match_found, "The log did not record the theft message!"