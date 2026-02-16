from typing import Dict, List, Literal
from pydantic import BaseModel, Field, create_model, field_validator, validator
from prompts.prompts import PromptLibrary


class AgentTurn(BaseModel):
    
    internal_monologue: str = Field(description=PromptLibrary.desc_monologue)
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
    
class AgentsAllowedToRespond(BaseModel):
    name: str = Field(description=PromptLibrary.desc_agent_names)
    allowed: bool = Field(description=PromptLibrary.desc_judge_allowed)
    @property
    def update_value(self):
        return self.allowed
    
class AgentScoreEntry(BaseModel):
    name: str = Field(description=PromptLibrary.desc_agent_names)
    score: int = Field(description=PromptLibrary.desc_judge_score)
    @property
    def update_value(self):
        return self.score

class AgentFormEntry(BaseModel):
    name: str = Field(description=PromptLibrary.desc_agent_names)
    form: str = Field(description=PromptLibrary.desc_judge_form)
    @property
    def update_value(self):
        return self.form
    
class JudgeTurn(BaseModel):
    internal_monologue: str = Field(description=PromptLibrary.desc_judge_monologue)
    complex_persona: DeepPersona = Field(description="The complex, evolving state of your psyche.")
    public_action: str = Field(description=PromptLibrary.desc_judge_action)
    public_response: str = Field(description=PromptLibrary.desc_judge_response)
    #ejection_target: str = Field(description=PromptLibrary.desc_ejection)
    create_new_agent: bool = Field(description=PromptLibrary.desc_create_new_agent)
    remove_agent: bool = Field(description=PromptLibrary.desc_remove_agent)
    lifeLesson: str = Field(description=PromptLibrary.desc_agent_lifeLessons)
    judgingCriteria: str = Field(description=PromptLibrary.desc_judge_judgingCriteria)
    
    scores: List[AgentScoreEntry] = Field(description=PromptLibrary.desc_judge_score)
    forms: List[AgentFormEntry] = Field(description=PromptLibrary.desc_judge_form)
    agent_response_allowed: List[AgentsAllowedToRespond] = Field(description=PromptLibrary.desc_judge_allowed)
    
    @property
    def agent_scores(self) -> dict:
        return {entry.name: entry.score for entry in self.scores}

class NewAgentManifest(BaseModel):
    private_thoughts: str = Field(description="Why are you creating this specific type of being?")
    name: str = Field(description="The name of the new agent.")
    form: str = Field(description="The pysical form of the new being.")
    persona: str = Field(description="The detailed personality and goal of this new agent. Make them harsh, rude, agressive")
    internal_monologue: str = Field("What's your thought proccess behind creating this particular agent?")
    public_response: str = Field(description="What you wish to publicly say to the agents about the creation of this new agent.")
    
class NewAgentRemoval(BaseModel):
    private_thoughts: str = Field(description="Why are you creating this killing this agent?")
    name: str = Field(description=f"The name of the agent you want to REMOVE from the game immediately (e.g., 'Zeldaton'). From")
    internal_monologue: str = Field("What's your thought proccess behind removing this particular agent?")
    public_response: str = Field(description="What you wish to publicly say to the agents about the removal of this agent.")

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


class BaseAgentResponse(BaseModel):
    """
    The master template for all agent interactions.
    Ensures every response has internal logic and a public statement.
    """
    private_thoughts: str = Field(
        description="Your internal thoughts. Strategy, feelings, and private observations."
    )
    public_response: str = Field(
        description="What you actually say out loud to the group. Stay in character!"
    )
    
class BaseResponse(BaseModel):
    private_thoughts: str
    public_response: str
    
    
class DynamicModelFactory:
    
    @classmethod
    def basic_turn_model(cls, name: str, public_response_prompt = None, private_thoughts_prompt = None, 
                         additional_thought_nudge: str = None, action_field: tuple = None):
     
        public_desc = public_response_prompt or PromptLibrary.desc_basic_public_response
        private_desc = private_thoughts_prompt or PromptLibrary.desc_basic_thought
        
        if additional_thought_nudge:
            private_desc = f"{private_desc} {additional_thought_nudge}"
            
        fields = {
            
            "public_response": (str, Field(description=public_desc)),
            "private_thoughts": (str, Field(description=private_desc))
        }
        
        # If the game has a specific action (like voting or split/steal), add it here
        if action_field:
            fields["action"] = action_field
            
        return create_model(name, __base__=BaseResponse, **fields)
    
    
    @classmethod
    def choose_agent_to_remove_model(cls, allowed_names):
        actionField= (Literal[tuple(allowed_names)], Field(
                description="The exact name of the agent to REMOVE."
                ))
        return cls.basic_turn_model("choose_agent_to_remove_model", action_field=actionField )
    
    @classmethod
    def prisoners_dilemma_model(cls):
        # Weigh the risks and benefits of splitting vs. stealing based on your personality and the other agent's past behavior.
            # - they seem to do this without prompting
        #"What you say out loud to the group while revealing your choice."
            # - some times they lie which is funny because their words are secret until the reveal anyway
        action = (Literal["split", "steal"], Field(description="Your final choice."))
        return cls.basic_turn_model(
            "Dilemma", 
            additional_thought_nudge="Will you cooperate or betray?", 
            action_field=action
        )
        
        
        
            
    
