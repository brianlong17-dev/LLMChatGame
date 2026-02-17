from models.game_models import DynamicGameModelFactory, SumariseRoundComplex

class GameMaster:
    def __init__(self, client, model_name: str):
        self.model_name = model_name
        self.client = client
    
    def choose_agent_based_on_parameter(self, gameBoard,allowed_names, parameter: str):
        ex = ("The most CHAOTIC player is the one that has the most unpredictable actions, and causes the most disruption to the other players. "
        "They are the wild card, and can be both a threat and an asset to the other players. They are often the most entertaining to watch, "
        "but also the most difficult to predict.")
        turn = self.client.create(
            model=self.model_name,
            response_model=DynamicGameModelFactory.choose_agent_based_on_parameter(allowed_names, parameter),
            messages=[
                {"role": "system", "content": f"You oversee this game. You help to make the information managable for the LLMs playing."},
                {"role": "user", "content": f"PAST SUMARRIES: {gameBoard.round_summaries} "
                 f"#########################"
                 f"Current round: {gameBoard.currentRound}"
                 f"You need to choose a single player that best represents this parameter: '{parameter}'."} 
            ]
        )
        return turn.nameToChoose #TODO rename
    def summariseRound(self, gameBoard): 
        turn = self.client.create(
            model=self.model_name,
            response_model=SumariseRoundComplex,
            messages=[
                {"role": "system", "content": f"You oversee this game. You help to make the information managable for the LLMs playing."},
                {"role": "user", "content": f"PAST SUMARRIES: {gameBoard.round_summaries} "
                 f"#########################"
                 f"Summarise the following round: {gameBoard.currentRound} Scores:  {gameBoard.agent_scores}"} 
            ]
        )
        return turn
    
    def most_chaotic_player(self, gameBoard): 
        turn = self.client.create(
            model=self.model_name,
            response_model=SumariseRoundComplex,
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
    
