from typing import Dict, List
from pydantic import BaseModel, Field, create_model, field_validator, validator
from prompts import PromptLibrary

class SumariseRoundBasic(BaseModel):
    round_summary: str = Field(description="A summary of the round to give to each player ")

class SumariseRoundComplex(BaseModel):
    round_summary: str = Field(description="A summary of the round to give to each player ")
    overall_story: str = Field(description="A summary of the over all story so far")
    narative_critique: str = Field(description=f"These are LLMs playing a game. Is it interesting to watch? "
                                   "Are the agents understanding the game?"
                                   "How should the LLMs be adjusted to make this more interesting for a human to follow?"
                                   "What would be an interesting thing to program into the game?"
                                   )

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
    thought_process: str = Field(description="Why are you creating this specific type of being?")
    name: str = Field(description="The name of the new agent.")
    form: str = Field(description="The pysical form of the new being.")
    persona: str = Field(description="The detailed personality and goal of this new agent. Make them harsh, rude, agressive")
    internal_monologue: str = Field("What's your thought proccess behind creating this particular agent?")
    public_response: str = Field(description="What you wish to publicly say to the agents about the creation of this new agent.")
    
class NewAgentRemoval(BaseModel):
    thought_process: str = Field(description="Why are you creating this killing this agent?")
    name: str = Field(description=f"The name of the agent you want to REMOVE from the game immediately (e.g., 'Zeldaton'). From")
    internal_monologue: str = Field("What's your thought proccess behind removing this particular agent?")
    public_response: str = Field(description="What you wish to publicly say to the agents about the removal of this agent.")
    
class FinalWords(BaseModel):
    thought_process: str = Field(description="HOW DO YOU FEEL? What do you think but wouldn't say? What are you privately thinking?")
    final_words: str = Field(description=f"YOU ARE ABOUT TO DIE. What are you final words to the players?")
    
def newAgentRemovalModel(AllowedNames):
    DynamicRemovalModel = create_model(
        'DynamicRemovalModel',
        thought_process=(str, Field(description="Why are you removing this agent?")),
        name=(str, Field(description=f"The exact name of the agent you want to REMOVE. From : {AllowedNames}")),
        internal_monologue=(str, Field(description="Your internal thoughts.")),
        public_response=(str, Field(description="Your public announcement."))
    )
    return DynamicRemovalModel

def votePlayerOffModel(AllowedNames):
    DynamicRemovalModel = create_model(
        'DynamicRemovalModel',
        thought_process=(str, Field(description="Why are you voting to remove this agent?")),
        name=(str, Field(description=f"The exact name of the agent you want to vote to REMOVE. From : {AllowedNames}")),
        internal_monologue=(str, Field(description="Your internal thoughts.")),
        public_response=(str, Field(description="Your public announcement. Who you're voting for and why?"))
    )
    return DynamicRemovalModel