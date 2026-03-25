from collections import deque
from pydantic import Field
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
from prompts.prompts import PromptLibrary
from agents.base_agent import BaseAgent
from typing import TYPE_CHECKING, Dict, Optional
if TYPE_CHECKING:
    from gameplay_management import *

class Debater(BaseAgent):
    
    
    def __init__(
        self,
        name: str,
        initial_persona: str,
        client,
        model_name: str,
        higher_model_name: str = None,
        speaking_style: str = "",
    ):
        super().__init__(name, client, model_name, higher_model_name=higher_model_name)
        self.rating = 0
        self.persona = initial_persona
        self.strategy_to_win = "WATCH AND UPDATE WITH A PLAN"
        self.mathematical_assessment = ""
        self.life_lessons = deque(maxlen=8)
        self.speaking_style = speaking_style
        self.phase_summaries_detailed = {}
        self.phase_summaries_brief = {}
        self.detailed_summary_count = 2
        self.game_over = False
        self.logging = False
        #todo : implement temperature
    
    # --- 1. CONFIGURATION (The Map) ---
    @property
    def field_mappings(self) -> Dict[str, str]:
        #TODO just allgin these
        return {
            "updated_persona_summary": "persona",
            "updated_strategy_to_win": "strategy_to_win",
            "mathematical_assessment": "mathematical_assessment",
            "lifeLesson": "life_lessons",
            "speaking_style": "speaking_style"
        }
        
    def logic_fields(self):
        return {
            "mathematical_assessment": (str, Field(description=PromptLibrary.desc_agent_mathematical_assessment))
        }
    
    def internal_thinking_fields(self):
        return {
            "updated_persona_summary": (str | None, Field(default = None, description=PromptLibrary.desc_persona_update)),
            "updated_strategy_to_win": (str| None, Field(default = None, description=PromptLibrary.desc_agent_updated_strategy_to_win)),
            "lifeLesson": (str, Field(description=PromptLibrary.desc_agent_lifeLessons)),
            "speaking_style":  (Optional[str], Field(default=None,description=PromptLibrary.desc_agent_speaking_style))
            #ideas - pass the current speaking style in- makes more intentional? keep old versions in a history, for dev to see evolution 
            
        }

    def cognitive_fields(self):
        return {**self.logic_fields(), **self.internal_thinking_fields()}
    
    def _system_prompt(self, gameBoard):
        return PromptLibrary.player_system_prompt(self, gameBoard)
      
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
        
        if instruction_override:
            instructions = instruction_override
        else:
            instructions = PromptLibrary.player_user_prompt(self.phase_summaries_string(),
                gameBoard.context_builder.get_full_context(self), gameBoard.score_string())

        # 2. Combine
        full_user_content = f"{instructions}\n\n{user_content}"
        return full_user_content
                     
    def take_turn_standard(self, user_content, gameBoard, model, system_content = None, instruction_override=None):
       
        user_content = self._get_full_user_content(gameBoard, user_content, instruction_override) #TODO this is a big refactoring
        turn = self.get_response(user_content, model, gameBoard, system_content) #TODO temperature
        self.process_turn_cognitive_fields(turn)
        return turn
    
    def phase_summaries_string(self):
        all_keys = set(self.phase_summaries_detailed.keys()).union(
            set(self.phase_summaries_brief.keys())
        )
        if not all_keys:
            return "No summaries yet.\n"
            
        sorted_keys = sorted(list(all_keys))
        total_summaries = len(sorted_keys)
        detailed_start_index = max(0, total_summaries - self.detailed_summary_count)
        
        string = ""
        
        for i, key in enumerate(sorted_keys):
            if i < detailed_start_index:
                summary = self.phase_summaries_brief.get(key) or self.phase_summaries_detailed.get(key, "Summary missing.")
                string += f"Phase {key}:\n{summary}\n\n"
            else:
                summary = self.phase_summaries_detailed.get(key) or self.phase_summaries_brief.get(key, "Summary missing.")
                string += f"Phase {key}:\n{summary}\n\n"
        return string 
    
    def _summarise_phase_context_string(self, game_board):
        phase_rounds_formatted = game_board.context_builder.phase_rounds_string(self)
        context_string = "------------YOUR PREVIOUS PHASE SUMMARIES-----------------\n"
        context_string += self.phase_summaries_string() #this should say none yet if empty.
        context_string += "\n\n------------ The current phase to summarise into memory: ---------\n"
        context_string += phase_rounds_formatted
        context_string += "-----------------------------------------------------------\n"
        return context_string
    
    def _build_summary_model(self):
        brief_summary_field = {"brief_summary" : (str, Field(description="Write an a brief summary of the phase from your perspective- Include the most essential strategic information you want to remember. A brief couple of bullet points. Eventually this will be all you have to access from early phases."))}
        public_response_prompt = "This is your summary- write in the first person, how you experienced the phase. Write every detail you think is important to commit to memory. This will only be seen by you."
        response_model = DynamicModelFactory.create_model_(
                self,
                model_name="sumariser",
                public_response_prompt=(public_response_prompt),
                private_thoughts_prompt=(
                    "What is important to remember?"
                ),
                action_fields = brief_summary_field
            )
        return response_model
        
    def summarise_phase(self, game_board):
        phase_number = game_board.phase_number
        prompt = ("From your perspective, write a summary of what happened in this phase. "
                  "Include all information that you think is relevant to retain, as this will be your memory of the game going forward."
                  "THIS IS PRIVATE- No one will see.")
        
        context_string = self._summarise_phase_context_string(game_board)
        self.use_higher_model = True
        response_model = self._build_summary_model()
        
        response = self.take_turn_standard(prompt, game_board, response_model, instruction_override=context_string)
        self.phase_summaries_detailed[phase_number] = response.public_response
        self.phase_summaries_brief[phase_number] = response.brief_summary
        
