import random

from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin


class HighestPointsImmunity(ImmunityMechanicsMixin):
    
    def display_name(self):
        return "Highest Points Player Immunity"

    def rules_description(self):
        rules_string = "The player with the highest points receives immunity from the next vote. "
        if self.cfg().immunity_highest_points_only_one:
            rules_string += "In the case of a tie, one player is randomly selected to receive immunity."
        else:
            rules_string +="In the case of a tie, all tied players receive immunity."
        return rules_string
        

    def run_immunity(self) -> list[str]:
        return self._highest_points_immunity(self.cfg().immunity_highest_points_only_one)

    def _highest_points_immunity(self, only_one: bool = False) -> list[str]:
        host_string = ""
        max_points = max(self.gameBoard.agent_scores.values())
        highest_players = [
            name for name, points in self.gameBoard.agent_scores.items() if points == max_points
        ]
        
        
        if len(highest_players) == 1:
            host_string = f"The player with the highest points, and therefore immune from the following vote is: {highest_players[0]}. Congrats!"
            
        elif only_one and len(highest_players) > 1:
            highest_players = [random.choice(highest_players)]
            host_string = f"As we have a tie for the top score, the player with highest points chosen at random is... {highest_players[0]}! Congrats!"
            
        else:
            names_string = ", ".join(name for name in highest_players)
            host_string = f"The players with the highest points, and therefore immune from the following vote are: {names_string}. Congrats!"
        
        self.gameBoard.host_broadcast(host_string)
        for agent_name in highest_players:
            winner = self._agent_by_name(agent_name)
            winner_response = self.respond_to(winner, host_string)
            self.publicPrivateResponse(winner, winner_response)
            
        return highest_players
