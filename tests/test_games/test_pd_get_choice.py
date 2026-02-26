import pytest
from unittest.mock import MagicMock, patch
#from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma

def test_get_split_or_steal_flow(pd_game):
    """
    Verifies that the game engine correctly:
    1. Formats the prompt with the opponent's name.
    2. Creates the correct 'Split/Steal' choices.
    3. Asks the player to take a turn.
    """
    
    # 1. SETUP: Create Fake Agents
    mock_player = MagicMock()
    mock_player.name = "Hero"
    
    mock_opponent = MagicMock()
    mock_opponent.name = "Villain"
    
    target_factory = "gameplay_management.game_prisoners_dilemma.DynamicModelFactory"
    target_prompt_lib = "gameplay_management.game_prisoners_dilemma.GamePromptLibrary"
    
    with patch(target_factory) as mock_factory, \
         patch(target_prompt_lib) as mock_library:
        
        # Configure the mocks to behave how we expect
        mock_library.pd_game_prompt = "Vs {opponent_name}" # Simple string template
        
        # Mock the helper method on the game class itself
        # (We don't want to test create_choice_field logic here, just that it was called)
        mock_field_definition = {"action": (str, "Field(...)")} 
        pd_game.create_choice_field = MagicMock(return_value=mock_field_definition)
        
        # Mock the Model Factory to return a dummy model object
        mock_model_obj = MagicMock()
        mock_factory.create_model_.return_value = mock_model_obj
        
        # Mock the player's response
        expected_response = "I choose split"
        mock_player.take_turn_standard.return_value = expected_response

        # 3. ACT: Call the method under test
        result = pd_game.get_split_or_steal(mock_player, mock_opponent)

        # 4. ASSERT: Did we get the response back?
        assert result == expected_response

        # 5. ASSERT: Did we create the choice fields correctly?
        pd_game.create_choice_field.assert_called_once_with("action", ["split", "steal"])

        # 6. ASSERT: Did we format the prompt correctly?
        # (The function creates 'user_content' internally, checking the call to player verifies it)
        mock_player.take_turn_standard.assert_called_once()
        
        # Verify arguments passed to player.take_turn_standard(user_content, gameBoard, model)
        args, _ = mock_player.take_turn_standard.call_args
        assert "Vs Villain" in args[0]  # The prompt should contain the formatted name
        assert args[2] == mock_model_obj # The model passed should be our mock from the factory