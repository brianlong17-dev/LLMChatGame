from typing import Dict, List, Literal, Optional, Type, TYPE_CHECKING
from pydantic import BaseModel, Field, create_model, field_validator, validator
from prompts.prompts import PromptLibrary

import warnings
if TYPE_CHECKING:
    from agents.human_player import Human
    from agents.player import Debater
    


class BaseResponse(BaseModel):
    private_thoughts: str = Field(description= PromptLibrary.desc_basic_thought)
    public_response: str = Field(description=PromptLibrary.desc_message)
    
    
class DynamicModelFactory:  
    
    @classmethod 
    def create_human_model(cls, public_response_prompt, action_fields):
        ordered_fields = {}
        if action_fields:
            ordered_fields.update(action_fields)
        pub_prompt = public_response_prompt or PromptLibrary.desc_message
        ordered_fields["public_response"] = (str, Field(description=pub_prompt))
        ordered_fields["private_thoughts"] = (str, Field(description="Private thoughts..."))
        return create_model('human_model', **ordered_fields)
        
    
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
        optional: bool = False
    ) -> Type[BaseModel]:
        if agent.is_human(): # and not agent.is_testing:
            return cls.create_human_model(public_response_prompt, action_fields)
            
        agent_logic_fields = agent.logic_fields()
        agent_complex_fields = agent.internal_thinking_fields()
        ordered_fields = {}
        #........ Scratch pad
        
        ordered_fields["who_are_you"] = (
                str, Field(description=f"Remind yourself of who you are, so you don't get confused")
            )
        ordered_fields["hallucination_catcher"] = (
                str, Field(description=f"In the past round do you see a hallucination or lie? Be careful not to repeat it")
            )
        ordered_fields["bandwagon"] = (
                str, Field(description=f"Is everyone jumping on a repeated thought? Do you agree? If not, say so")
            )
        if game_logic_fields:
            ordered_fields.update(game_logic_fields)
            
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
                base_thought = "What are you secretly thinking? How you really feel, not revealed to anyone."
            else:
                base_thought = PromptLibrary.desc_basic_thought
        else:
            base_thought = private_thoughts_prompt
            
        if optional and agent.optional_response_buffer < 1:
            base_thought += f" Note: this is a round with an optional response. To choose to respond will cost 1 point from your optional response buffer at: {agent.optional_response_buffer}."
        ordered_fields["private_thoughts"] = (str, Field(description=base_thought))
        
        #....action 
        if action_fields:
            ordered_fields.update(action_fields)
        #...... public response
        pub_prompt = public_response_prompt or PromptLibrary.desc_message
        
        if optional:
            ordered_fields["public_response"] = (Optional[str], Field(default=None, description=(f"{pub_prompt} Your optional response buffer is at: {agent.optional_response_buffer}. "
                f"Leave null if you have nothing to add. If you choose silence, leave this blank - do not announce that you are staying silent. ")))
        else:
            ordered_fields["public_response"] = (str, Field(description=pub_prompt))
        #........ self-learning
        if agent_complex_fields:
            ordered_fields.update(agent_complex_fields)

        return create_model(model_name, **ordered_fields)
    

     
    
