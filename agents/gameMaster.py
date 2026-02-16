from models.game_models import SumariseRoundComplex

class GameMaster:
    def __init__(self, client, model_name: str):
        self.model_name = model_name
        self.client = client
        
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
        
    def compressRounds(self, rounds):
        return ("")
    
