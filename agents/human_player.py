from collections import deque
from pydantic import Field, ValidationError
from agents.player import Debater
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
from prompts.prompts import PromptLibrary
from agents.base_agent import BaseAgent
from typing import TYPE_CHECKING, Dict, Optional
if TYPE_CHECKING:
    from gameplay_management import *

class Human(Debater):
    
    
    def __init__(
        self,
        name: str
    ):
        super().__init__(name = name,
        initial_persona= '',
        client = None,
        model_name = None,
        higher_model_name= None,
        speaking_style = "")
        #todo : implement temperature
    
    def is_human(self):
        return True
    
    def get_multiple_choice(self, prompt, choices):
        print(prompt)
        print(choices)
        # Keep asking until they give a valid answer
        while True:
            choice = input(f"\n {prompt}: ")
            
            if choice in choices:
                return (choice) # Return as an integer so it's easy to use later
            else:
                print("Invalid input.")
        
    def get_response(self, user_content: str, response_model, gameBoard, system_content: str = None):
        print("\n" + "="*50)
        print("👤 HUMAN AGENT TURN")
        print("="*50)
        
        # 1. Show the human the exact same context the AI gets
        actual_system_content = system_content or self._system_prompt(gameBoard)
        #print(f"\n[CURRENT GAME STATE]:\n{actual_system_content}")
        #TODO make a setting where you get all the player info...
        print(f"\n[PROMPT]:\n{user_content}")
        print("-" * 50)

        # 2. Extract fields dynamically (supports both Pydantic v1 and v2)
        fields = getattr(response_model, 'model_fields', getattr(response_model, '__fields__', {}))
        
        # 3. Loop until the human provides valid data
        while True:
            answers = {}
            
            for field_name, field_info in fields.items():
                if field_name == "private_thoughts":
                    answers[field_name] = "" # Automatically assign a blank string
                    continue
                description = field_info.description or f"Enter value for {field_name}"
                
                print(f"\n▶ {field_name.upper()}")
                print(f"  Goal: {description}")
                
                # Get input from the terminal
                user_input = input("  >> ")
                answers[field_name] = user_input
                
            try:
                # 4. Instantiate the Pydantic model exactly like the LLM client does
                response = response_model(**answers)
                print("\n✅ Response accepted!")
                
                # This return matches your AI get_response PERFECTLY
                return response
                
            except ValidationError as e:
                # If Pydantic rejects the input (e.g., expected an int, got a string)
                print("\n❌ FORMAT ERROR: The game engine rejected your input.")
                
                # Print a clean version of the Pydantic error so you know what to fix
                for error in e.errors():
                    print(f" - Field '{error['loc'][0]}': {error['msg']}")
                    
                print("Let's try filling that out again...\n")
    #def make turn 
    #get public response, plus action fields