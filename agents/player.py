from collections import deque
from pydantic import Field
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
from prompts.prompts import PromptLibrary
from agents.base_agent import BaseAgent
from typing import TYPE_CHECKING, Dict
if TYPE_CHECKING:
    from gameplay_management import *

class Debater(BaseAgent):
    
    
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str, speaking_style: str = ""):
        super().__init__(name, client, model_name)
        self.rating = 0
        self.persona = initial_persona
        self.form = initial_form #I think it helps them be defined 
        self.strategy_to_win = "WATCH AND UPDATE WITH A PLAN"
        self.mathematicalAssessment = ""
        self.life_lessons = deque(maxlen=8)
        self.speaking_style = speaking_style
        
        #todo : implement temperature
    
    # --- 1. CONFIGURATION (The Map) ---
    @property
    def field_mappings(self) -> Dict[str, str]:
        """
        Maps Pydantic Field Name -> Agent Attribute Name.
        """
        return {
            "updated_persona_summary": "persona",
            "updated_strategy_to_win": "strategy_to_win",
            "mathematicalAssessment": "mathematicalAssessment",
            "lifeLesson": "life_lessons",
            "speaking_style": "speaking_style"
        }
        
    def logic_fields(self):
        return {
            "mathematicalAssessment": (str, Field(description=PromptLibrary.desc_agent_mathematicalAssessment))
        }
    
    def internal_thinking_fields(self):
        return {
            "updated_persona_summary": (str, Field(description=PromptLibrary.desc_persona_update)),
            "updated_strategy_to_win": (str, Field(description=PromptLibrary.desc_agent_updated_strategy_to_win)),
            "lifeLesson": (str, Field(description=PromptLibrary.desc_agent_lifeLessons)),
            "speaking_style": (str, Field(description="ONLY RETURN TO MODIFY EXISTING SPEAKING STYLE, ELSE BLANK. Optional- speaking style- how your character speaks, the charactaristics of how they use their words. If you want to evolve your existing 'Speaking Style', if you feel your character is evolving")),
            
        }

    def cognitive_fields(self):
        return {**self.logic_fields(), **self.internal_thinking_fields()}
    
    def _system_prompt(self, gameBoard):
        return PromptLibrary.player_system_prompt(self, gameBoard)
    
    def _check_if_empty(self, text: str):
        if not text:
            return True
        clean_text = text.strip().rstrip('.').lower()
        return clean_text in self.lazy_responses() 
        
    def process_turn_cognitive_fields(self, turn):
        
        simple_personality_fields = self.cognitive_fields()
        for field_name in simple_personality_fields:
            value = getattr(turn, field_name, None)
            if self._check_if_empty(value):
                continue
            target_attr_name = self.field_mappings.get(field_name)
            if not target_attr_name:
                continue #ie could maybe include mathemtical assesment 
            
            
            current_attr_value = getattr(self, target_attr_name)
            # if its a queue we need to append
            if isinstance(current_attr_value, (list, deque)):
                clean_val = value.strip()
                # Check for duplicates (case-insensitive)
                is_duplicate = any(clean_val.lower() == existing.lower() for existing in current_attr_value)
                if not is_duplicate:
                    current_attr_value.append(clean_val)
            else:
                setattr(self, target_attr_name, value)
    
    def _get_full_user_content(self, gameBoard, user_content, instruction_override=None) :
        
        # 1. Choose the instruction wrapper
        if instruction_override:
            instructions = instruction_override
        else:
            # Default to the standard "Play to Win" prompt
            instructions = PromptLibrary.player_user_prompt(gameBoard.get_full_context())

        # 2. Combine
        full_user_content = f"{instructions}\n\n{user_content}"
        return full_user_content
                     
    def take_turn_standard(self, user_content, gameBoard, model, system_content = None, append_complex_fields = True, instruction_override=None):
        #Human player split will be here---- needing to demark the required fields is the question.
        #it is only public words and action, and anyway, public words isnt even required.
        
        user_content = self._get_full_user_content(gameBoard, user_content, instruction_override) #TODO this is a big refactoring
        turn = self.get_response(user_content, model, gameBoard, system_content) #TODO temperature
        self.process_turn_cognitive_fields(turn)
        return turn
    

    
    
