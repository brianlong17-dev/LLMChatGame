from typing import Literal
from pydantic import BaseModel, Field, create_model

class SumamriseRoundBasic(BaseModel):
    round_summary: str = Field(description="A summary of the round to give to each player")
    
class DynamicGameModelFactory:
    #depreciate i guess... altho why isnt it better here?
    @classmethod
    def choose_agent_based_on_parameter(cls, allowed_names, parameter: str):
        return create_model("ChooseAgentBasedOnParameter",
            nameToChoose=(Literal[tuple(allowed_names)], Field(
                description=f"The exact name of the agent to choose. Only the players in the allowed names are valid. "
                f"Allowed names: {allowed_names}. The parameter for choosing: {parameter}")),
            thought_proccess=(str, Field(description="What's your thought proccess behind this decision?"))
        )
        

class SummariseRoundComplex(BaseModel):
    round_summary: str = Field(description="A summary of the round. What information would an LLM agent player need to know? Condensed for LLM readability")
    overall_story: str = Field(description="A summary of the over all story so far")
    narative_critique: str = Field(description=f"These are LLMs playing a game. Is it interesting to watch? "
                                   "Are the agents understanding the game?"
                                   "How should the LLMs be adjusted to make this more interesting for a human to follow?"
                                   "What would be an interesting thing to program into the game?"
                                   )
