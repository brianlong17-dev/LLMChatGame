from gameplay_management.game_targeted.game_targeted_choice import GameTargetedChoice
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class GameTargetedChoiceGive(GameTargetedChoice):
    
    @classmethod
    def display_name(cls, cfg):
        return "Giver"

    @classmethod
    def rules_description(cls, cfg):
        return "Choose a player to receive points!"
    
    def run_game(self):
        self.run_game_give()
     
    def run_game_give(self):
        points_amount = GamePromptLibrary.targeted_games_points
        game_intro = GamePromptLibrary.give_game_intro #really should this be merged with the game def.
        player_intro = GamePromptLibrary.give_game_player_intro
        game_instruction = f"Choose one player from to receive {points_amount} points. Explain why."
        
        
        def give_points_model(player):
            other_agent_names = [name for name in self.gameBoard.agent_names() if name != player.name]
            action_fields = self._choose_name_field(other_agent_names, game_instruction) #player intro is not correct here
            return DynamicModelFactory.create_model_(player, model_name="GivePointsModel", action_fields=action_fields) 
            
        def give_points_logic(player, target_agent, _response): #response is only needed for subtraction
            result_host_string = f"Yay! {player.name} chooses {target_agent.name}! They receive {points_amount} points."
            self.gameBoard.append_agent_points(target_agent.name, points_amount)
            return(result_host_string, target_agent)
        
        self.run_targeted_round(game_intro, player_intro, game_instruction, give_points_logic, give_points_model)
   