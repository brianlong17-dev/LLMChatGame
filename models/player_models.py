from typing import Dict, List, Literal, Type
from pydantic import BaseModel, Field, create_model, field_validator, validator
from prompts.prompts import PromptLibrary
import warnings


class AgentTurn(BaseModel):
    private_thoughts: str = Field(description=PromptLibrary.desc_basic_thought)
    public_response: str = Field(description=PromptLibrary.desc_message)
    updated_persona_summary: str = Field(description=PromptLibrary.desc_persona_update)
    updated_strategy_to_win: str = Field(description=PromptLibrary.desc_agent_updated_strategy_to_win)
    public_action: str = Field(description=PromptLibrary.desc_action_agent)
    public_response: str = Field(description=PromptLibrary.desc_message)
    lifeLesson: str = Field(description=PromptLibrary.desc_agent_lifeLessons)
    
class DeepPersona(BaseModel):
    core_identity: str = Field(description=PromptLibrary.dp_core_identity)
    current_mood: str = Field(description=PromptLibrary.dp_current_mood)
    hidden_agenda: str = Field(description=PromptLibrary.dp_hidden_agenda)
    speaking_style: str = Field(description=PromptLibrary.dp_speaking_style)
    

#TBR with Response
class FinalWords(BaseModel):
    private_thoughts: str = Field(description="HOW DO YOU FEEL? What do you think but wouldn't say? What are you privately thinking?")
    final_words: str = Field(description=f"YOU ARE ABOUT TO DIE. What are you final words to the players?")

    
class AgentReaction(BaseModel):
    private_thoughts: str = Field(
        description="Your internal reaction to the event. Note who betrayed you, who cooperated, and how this impacts your strategy."
    )
    public_response: str = Field(
        description="What you say out loud to the group in response to the news. React in character."
    )


class BaseResponse(BaseModel):
    private_thoughts: str = Field(description= PromptLibrary.desc_basic_thought)
    public_response: str = Field(description=PromptLibrary.desc_message)
    
    
class DynamicModelFactory:  
    
    @classmethod
    def _check_existing_complex_fields(cls, complex_fields, base_turn_model):
        existing_fields = getattr(base_turn_model, 'model_fields', {}).keys()
        overlaps = [key for key in complex_fields if key in existing_fields]
        if overlaps:
            warnings.warn(
            f"Model '{base_turn_model.__name__}' already contains fields: {overlaps}. "
            "These are being overwritten by with_complex_fields().",
            UserWarning
        )
    
    @classmethod
    def with_complex_fields(cls, base_turn_model: Type[BaseModel]):
            # updated_persona_summary: str = PromptLibrary.desc_persona_update,
            # updated_strategy_to_win: str = PromptLibrary.desc_agent_updated_strategy_to_win,
            # lifeLesson: str = PromptLibrary.desc_agent_lifeLessons):
        
        complex_fields = {
            "updated_persona_summary": (str, Field(description= PromptLibrary.desc_persona_update)),
            "updated_strategy_to_win": (str, Field(description=PromptLibrary.desc_agent_updated_strategy_to_win)),
            "lifeLesson": (str, Field(description=PromptLibrary.desc_agent_lifeLessons)),
            "mathematicalAssessment": (str, Field(description=PromptLibrary.desc_agent_mathematicalAssessment))
        }
        #TODO this is just to flag.. it shouldnt happen ...
        cls._check_existing_complex_fields(complex_fields, base_turn_model)
        
        return create_model(
            "ComplexTurn", 
            __base__=base_turn_model, 
            **complex_fields
        )
        
  
    @classmethod
    def _basic_fields_prompt_model(cls, public_response_prompt = None, private_thoughts_prompt = None, 
                         additional_thought_nudge: str = None):
        fields = {}
        #Only overwrite if there's a specific prompt
        #Anyway depreciate, you should be passing **fields if you want to do this
        
        if public_response_prompt:
            fields["public_response"] = (str, Field(description=public_response_prompt))
        if private_thoughts_prompt or additional_thought_nudge:
            base_thought = private_thoughts_prompt or BaseResponse.model_fields["private_thoughts"].description
            if additional_thought_nudge:
                base_thought = f"{base_thought} {additional_thought_nudge}"
                fields["rethink"] = (str, Field(description="Lets just doublecheck your thoughts. Consider the score. Consider what you can win. Consider the next vote " + additional_thought_nudge))
            fields["private_thoughts"] = (str, Field(description=base_thought))
            
        return fields
    
    @classmethod
    def basic_turn_model(cls, name: str = "basic_turn_model", public_response_prompt = None, private_thoughts_prompt = None, 
                         additional_thought_nudge: str = None, action_field: tuple = None):
        
        fields = cls._basic_fields_prompt_model(public_response_prompt, private_thoughts_prompt, additional_thought_nudge)

        # Action: like vote a player, split or steal. Single answer games 
        if action_field:
            fields["action"] = action_field
            
          
        return create_model(name, __base__=BaseResponse, **fields)
    
    
    @classmethod
    def final_words(cls):
        private_thoughts_prompt = "HOW DO YOU FEEL? What do you think but wouldn't say? What are you privately thinking?"
        public_response_prompt = "YOU ARE ABOUT TO DIE. What are you final words to the players?"
        return cls.basic_turn_model("final_words", public_response_prompt = public_response_prompt, private_thoughts_prompt = private_thoughts_prompt)


    @classmethod
    def choose_agent_to_remove_model(cls, allowed_names):
        context = "The exact name of the agent to REMOVE."
        return cls.choose_name_model(allowed_names, context)

    
    @classmethod
    def choose_name_model(cls, allowed_names, reason_for_choosing_prompt: str = "", model_name = "choose_agent_name", additional_thought_nudge = None):
        actionField= (Literal[tuple(allowed_names)], Field(
                description=f"The exact name of the agent. {reason_for_choosing_prompt}"
                ))
        return cls.basic_turn_model(model_name, action_field=actionField, additional_thought_nudge = additional_thought_nudge)
    
    
    
    @classmethod
    def prisoners_dilemma_model(cls):
        # Weigh the risks and benefits of splitting vs. stealing based on your personality and the other agent's past behavior.
            # - they seem to do this without prompting
        #"What you say out loud to the group while revealing your choice."
            # - some times they lie which is funny because their words are secret until the reveal anyway
            
        #should we nudge them to think about math here
        action = (Literal["split", "steal"], Field(description="Your final choice."))
        return cls.basic_turn_model(
            "Dilemma",  #this is more havy handed than id like but whatever
            additional_thought_nudge="What points are available? How will the next elimination work? Do you need points or alliance? ", 
            action_field=action
        )
        
        
            
    
