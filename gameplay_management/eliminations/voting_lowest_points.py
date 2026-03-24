from typing import Optional, Sequence

from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin


class VoteLowestPoints(VoteMechanicsMixin):
    @classmethod
    def display_name(cls, cfg):
        return "Fairwell, to thee of points so lowest"

    @classmethod
    def rules_description(cls, cfg):
        return "Player with the lowest points is removed from the game"
    
    def rules_description_detailed(self):
        #in future, potential tie breaker can be in config
        return (f"The player with the lowest score will now be removed from the game. "
                f"In the event of a tie, a player will be chosen at random.\n\n")

    def run_vote(self, immunity_players: Optional[Sequence[str]]):
        self.run_voting_lowest_points_removed(immunity_players)
    
    def run_voting_lowest_points_removed(self, immunity_players: Optional[Sequence[str]] = None, with_pass_option: bool = False):
        immunity_players = self._validate_immunity(immunity_players)
        players_up_for_elimination = self._players_up_for_elimination(immunity_players)
        player = self.get_strategic_players(players_up_for_elimination, top_player = False)[0]
        #TODO potentially, there can be a unified host string, alarms, plus rules.
        host_string = f"🚨🚨🚨 The time... has come. "
        host_string += VoteLowestPoints.rules_description_detailed(self)
        
        self.gameBoard.host_broadcast(host_string)
        self.gameBoard.host_broadcast(f"The player with the lowest score and will therefore, be removed from the competition is... {player.name}")
        self.eliminate_player_by_name(player.name)
   
