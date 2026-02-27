from typing import Literal

from pydantic import BaseModel, Field, create_model
from agents.base_agent import BaseAgent
from models.game_models import DynamicGameModelFactory, SummariseRoundComplex
from models.player_models import BaseResponse
from prompts.prompts import PromptLibrary

class GameMaster(BaseAgent):
    def __init__(self, client, model_name: str, higher_model_name: str = None, name ="Summariser"):
        super().__init__(name, client, model_name, higher_model_name=higher_model_name)
        self.color = "YELLOW"
        
    def _system_prompt(self, gameBoard):
        #TODO spruce up with the other one
        return ( f"You oversee this game. You help to make the information managable for the LLMs playing."
                f"PAST SUMARRIES: {gameBoard.round_summaries} "
                 f"#########################"
                 f"Current round: {gameBoard.currentRound}")
    
    
    def choose_agent_based_on_parameter(self, gameBoard,allowed_names, parameter: str):
        #TODO
        #ex = ("The most CHAOTIC player is the one that has the most unpredictable actions, and causes the most disruption to the other players. "
        #"They are the wild card, and can be both a threat and an asset to the other players. They are often the most entertaining to watch, "
        #"but also the most difficult to predict.")
        agent_names = gameBoard.agent_names
        #---------------
        choice_definition = (Literal[*agent_names], Field(description=parameter))
        fields = {"target_name" : choice_definition}
        response_model = create_model("choose_agent_based_on_parameter", __base__=BaseResponse, **fields)
        user_content = (f"You need to choose a single player that best represents this parameter: '{parameter}'.")
        return self.get_response(user_content, response_model, gameBoard, system_content = None)
        #---------------
    
    def summariseRound(self, gameBoard): 
        turn = self.client.create(
            model=self.model_name,
            response_model=SummariseRoundComplex,
            messages=[
                {"role": "system", "content": f"You oversee this game. You help to make the information managable for the LLMs playing."},
                {"role": "user", "content": f"PAST SUMARRIES: {gameBoard.round_summaries} "
                 f"#########################"
                 f"#########################"
                 f"Summarise the following round: {gameBoard.currentRound} Scores:  {gameBoard.agent_scores}"} 
            ]
        )
        return turn
    
    def most_chaotic_player(self, gameBoard): 
        turn = self.client.create(
            model=self.model_name,
            response_model=SummariseRoundComplex,
            messages=[
                {"role": "system", "content": f"You oversee this game. You help to make the information managable for the LLMs playing."},
                {"role": "user", "content": f"PAST SUMARRIES: {gameBoard.round_summaries} "
                 f"#########################"
                 f"Summarise the following round: {gameBoard.currentRound} Scores:  {gameBoard.agent_scores}"} 
            ]
        )
        return turn
        
    def compressRounds(self, rounds):
        return ("")
    
