
from gameplay_management.game_targeted.game_targeted_choice import *


class GameTargetedChoiceSteal(GameTargetedChoice):
    
    @classmethod
    def display_name(cls, cfg):
        return "Stealer"

    @classmethod
    def rules_description(cls, cfg):
        return "Choose a player to steal points from!"
    
    def run_game(self):
        self.run_game_steal()
        
        
    def run_game_steal(self):
        points_amount = GamePromptLibrary.targeted_games_points
        game_intro = (f"Well, it's time to lay down your mark.. "
        f"In this round, you will get to STEAL. Whatever player you pick, you will receive {points_amount} points... and they will LOSE them! "
        f"If you choose a player with less than {points_amount} points, their points wont go below zero, and you won't receive the full {points_amount} points." )
        player_intro = ("{player_name}! You're up- what player are you choosing to steal from, and why?") #can format this later?
        game_instruction = (f"Choose one player from to steal {points_amount} points from."
                            f"If you steal from a player with less than {points_amount}, you'll only get whatever points the have, maybe zero."
                            f"The name of the player who's points you are going to STEAL:")
        thought_nudge = (f"If you try to steal from someone with 0 points, you essentially pass.")
        
        def steal_points_model(player):
            other_agent_names = [name for name in self.gameBoard.agent_names() if name != player.name]
            action_fields = self._choose_name_field(other_agent_names, game_instruction)
            return DynamicModelFactory.create_model_(
                agent=player, 
                model_name="StealPointsModel", 
                action_fields=action_fields,
                additional_thought_nudge=thought_nudge
            )
        def steal_points_logic(player, target_agent, _response):
            current_victim_points = self.gameBoard.get_agent_score(target_agent.name)
            actual_steal = min(points_amount, max(0, current_victim_points))
            
            if actual_steal <= 0:
                result_host_string = (
                    f"Awkward... {player.name} tried to steal from {target_agent.name}, "
                    f"but they have empty pockets! No points changed hands."
                )
                player_for_reaction = player 
            else:
                result_host_string = (
                    f"Oooooh! {player.name} steals from {target_agent.name}! "
                    f"{player.name} gains {actual_steal} points, and {target_agent.name} loses them!"
                    
                )
                player_for_reaction = target_agent
            
            # Update the board
            self.gameBoard.append_agent_points(player.name, actual_steal)
            self.gameBoard.append_agent_points(target_agent.name, -actual_steal)
            return result_host_string, player_for_reaction
        self.run_targeted_round(game_intro, player_intro, game_instruction, steal_points_logic, steal_points_model)
      
