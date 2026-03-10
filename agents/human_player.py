from collections import deque
from pydantic import Field, ValidationError
from agents.player import Debater
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
from prompts.prompts import PromptLibrary
from agents.base_agent import BaseAgent
from typing import TYPE_CHECKING, Dict, Optional
import questionary

if TYPE_CHECKING:
    from gameplay_management import *

class Human(Debater):
    
    
    def __init__(self, name: str):
        super().__init__(name = name, initial_persona= '', client = None, model_name = None,
                         higher_model_name= None, speaking_style = "")
        self.is_testing = True
    
    def is_human(self):
        return True
    
    def multiple_choice(self, field_name, description, choices):
        
        print(f"\n▶ {field_name.upper()}")
        
        choice = questionary.select(
            description,
            choices=choices
        ).ask()
        return choice
    
    def single_input(self, field_name, description):
        
        print(f"\n▶ {field_name.upper()}")
        print(f"  Goal: {description}")
        return input("  >> ")

    def get_response(self, user_content: str, response_model, gameBoard, system_content: str = None):
        #print("\n" + "="*50)
        #print("👤 HUMAN AGENT TURN")
        #print("="*50)
        
        actual_system_content = system_content or self._system_prompt(gameBoard)
        
        if self.is_testing:
            print(f"\n[CURRENT GAME STATE]:\n{actual_system_content}")
            print(f"\n[PROMPT]:\n{user_content}")
        print("-" * 50)

        fields = getattr(response_model, 'model_fields', getattr(response_model, '__fields__', {}))
        while True:
            answers = {}
            for field_name, field_info in fields.items():
                if field_name == "private_thoughts":
                    answers[field_name] = "" # Automatically assign a blank string
                    continue
                
                description = field_info.description or f"Enter value for {field_name}"
                
                annotation = field_info.annotation
                
                if hasattr(annotation, "__args__"):
                    choices = [str(a) for a in annotation.__args__]
                    user_input = self.multiple_choice(field_name, description, choices)
                    
                else:
                    user_input = self.single_input(field_name, description)
                    
                answers[field_name] = user_input
                
            try:
                response = response_model(**answers)
                print("\n✅ Response accepted!")
                return response
                
            except ValidationError as e:
                print("\n❌ FORMAT ERROR: The game engine rejected your input.")
                for error in e.errors():
                    print(f" - Field '{error['loc'][0]}': {error['msg']}")
                print("Let's try filling that out again...\n")
    #def make turn 
    #get public response, plus action fields