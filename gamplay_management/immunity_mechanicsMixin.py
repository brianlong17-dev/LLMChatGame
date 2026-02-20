from gamplay_management.base_manager import BaseManager
#from core.gameboard import GameBoard
import random


class ImmunityMechanicsMixin(BaseManager):
    def __init__(self, gameBoard, simulationEngine):
        super().__init__(gameBoard, simulationEngine) 
        
                    
    def get_wildcard_player_immunity(self):
        # This is an example of a dynamic immunity type that the judge could call on. It gives immunity to the player with the most chaotic playstyle.
        wildcard_player = self.gameBoard.game_master.choose_agent_based_on_parameter(self.gameBoard, self.gameBoard.agent_names, "chaotic")
        return wildcard_player
    
    def get_highest_points_players_immunity_only_one(self):
        return self.get_highest_points_players_immunity(only_one = True)
    
    def get_highest_points_players_immunity(self, only_one = False):
        # This is an example of a dynamic immunity type that the judge could call on. It gives immunity to the player with the highest points.
        max_points = max(self.gameBoard.agent_scores.values())
        highest_players = [name for name, points in self.gameBoard.agent_scores.items() if points == max_points]
        if only_one and len(highest_players) > 1:
            highest_players = [random.choice(highest_players)]
        return highest_players
    
    