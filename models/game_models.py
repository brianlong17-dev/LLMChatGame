from pydantic import BaseModel, Field

class SumariseRoundBasic(BaseModel):
    round_summary: str = Field(description="A summary of the round to give to each player")

class SumariseRoundComplex(BaseModel):
    round_summary: str = Field(description="A summary of the round to give to each player ")
    overall_story: str = Field(description="A summary of the over all story so far")
    narative_critique: str = Field(description=f"These are LLMs playing a game. Is it interesting to watch? "
                                   "Are the agents understanding the game?"
                                   "How should the LLMs be adjusted to make this more interesting for a human to follow?"
                                   "What would be an interesting thing to program into the game?"
                                   )
