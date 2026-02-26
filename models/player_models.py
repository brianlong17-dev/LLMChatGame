from typing import Dict, List, Literal, Type, TYPE_CHECKING
from pydantic import BaseModel, Field, create_model, field_validator, validator
from prompts.prompts import PromptLibrary
import warnings
if TYPE_CHECKING:
    from agents.player import Debater


class BaseResponse(BaseModel):
    private_thoughts: str = Field(description= PromptLibrary.desc_basic_thought)
    public_response: str = Field(description=PromptLibrary.desc_message)
    
    
class DynamicModelFactory:  
    
    @classmethod
    def create_model_(
        cls, 
        agent: 'Debater', 
        model_name: str = "DynamicTurnModel",
        public_response_prompt: str = None, 
        private_thoughts_prompt: str = None, 
        additional_thought_nudge: str = None, 
        game_logic_fields: Dict[str, tuple] = None,   # Logic fields prompted by the game
        action_fields: Dict[str, tuple] = None,       # Actions required by the game (e.g. dropdowns)
        
    ) -> Type[BaseModel]:
        agent_logic_fields = agent.logic_fields()
        agent_complex_fields = agent.internal_thinking_fields()
        ordered_fields = {}
        #........ Scratch pad
        if game_logic_fields:
            ordered_fields.update(game_logic_fields)
        ordered_fields["who_are_you"] = (
                str, Field(description=f"Remind yourself of who you are, so you don't get confused")
            )
        ordered_fields["hallucination_catcher"] = (
                str, Field(description=f"In the past round do you see a hallucination or lie? Be careful not to repeat it")
            )
        ordered_fields["bandwagon"] = (
                str, Field(description=f"Is everyone jumping on a repleating a thought? Do you agree? If not, say so")
            )
            
        if agent_logic_fields:
            ordered_fields.update(agent_logic_fields)
        # I guess this should merge with game logic fields .... i just like the thouht being different base on this
        #TODO depreciate
        if additional_thought_nudge:
            ordered_fields["logic_processing"] = (
                str, Field(description=f"Work through the logic step-by-step: {additional_thought_nudge}")
            )
        
            
        #......... Thoughts
        if not private_thoughts_prompt:
            if agent_logic_fields or game_logic_fields or additional_thought_nudge:
                base_thought = "Based on the logic and math above, how are you feeling? What are your secret intentions?"
            else:
                base_thought = PromptLibrary.desc_basic_thought
        else:
            base_thought = private_thoughts_prompt
        ordered_fields["private_thoughts"] = (str, Field(description=base_thought))
        
        #....action 
        if action_fields:
            ordered_fields.update(action_fields)
        #...... public response 
        pub_prompt = public_response_prompt or PromptLibrary.desc_message
        ordered_fields["public_response"] = (str, Field(description=pub_prompt))
        #........ self-learning
        if agent_complex_fields:
            ordered_fields.update(agent_complex_fields)
            
        return create_model(model_name, **ordered_fields)
    

     
    
