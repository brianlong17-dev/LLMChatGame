from collections import deque
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
        self.round_summaries = deque(maxlen=50)
        self.name = "Host"
    
    
    def _system_prompt(self, gameBoard):
        #TODO spruce up with the other one
        #Used in the wildcard selection
        return ( f"You oversee this game. You help to make the information manageable for the LLMs playing."
                f"PAST SUMARRIES: {"\n".join(self.round_summaries)} "
                 f"#########################"
                 f"Current round: {gameBoard.context_builder.current_round_formatted(self)}")
    
    
    def choose_agent_based_on_parameter(self, gameBoard, allowed_names, parameter: str):
        #TODO
        if parameter == "chaotic":
            parameter = ("The most CHAOTIC player is the one that has the most unpredictable actions, and causes the most disruption to the other players. "
        "They are the wild card, and can be both a threat and an asset to the other players. They are often the most entertaining to watch, "
        "but also the most difficult to predict.")
        #---------------
        choice_definition = (Literal[*allowed_names], Field(description=parameter))
        public_reason = (str, Field(description="The public announcement as to why this player was chosen. Give answer in the third person passive voice."))
        fields = {"target_name" : choice_definition, "public_reason" : public_reason}
        response_model = create_model("choose_agent_based_on_parameter", __base__=BaseResponse, **fields)
        user_content = (f"You need to choose a single player that best represents this parameter: '{parameter}'.")
        return self.get_response(user_content, response_model, gameBoard, system_content = None)
        #---------------
    
    def summariseRound(self, gameBoard): 
        turn = self.client.create(
            model=self.model_name,
            response_model=SummariseRoundComplex,
            messages=[
                {"role": "system", "content": f"You oversee this game. You help to make the information manageable for the LLMs playing."},
                {"role": "user", "content": f"PAST SUMARRIES: {"\n".join(self.round_summaries)} "
                 f"#########################"
                 f"#########################"
                 f"Summarise the following round: {gameBoard.context_builder.current_round_formatted(self)} Scores:  {gameBoard.agent_scores}"} 
            ]
        )
        self.round_summaries.append(turn.round_summary)
        return turn
    
    def summarise_game_text(self, context, game_text):
        model = DynamicGameModelFactory.cycle_game_compression_model()
        turn = self.client.create(
            model=self.model_name,
            response_model=model,
            messages=[
                {"role": "system", "content": f"You oversee this game. You help to make the information manageable for the LLMs playing."},
                {"role": "user", "content": f"Previous game context:\n{context}"
                 f"#########################"
                 f"#########################"
                 f"Summarise the following segment: {game_text}"} 
            ]
        )
        print("\n\nContext: \n" + context )
        print("\n\nGame text: \n" + game_text)
        print("\n\nSummary: \n" + turn.summary )
        
        return turn.summary
