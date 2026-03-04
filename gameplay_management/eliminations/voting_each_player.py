from typing import Optional, Sequence

from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.gamePrompts import GamePromptLibrary


class VoteEachPlayer(VoteMechanicsMixin):
    def display_name(self):
        return "Direct Democracy"

    def rules_description(self):
        return "Each player votes to eliminate, the player with the most votes in removed."
        
    
    def rules_description_detailed(self):
        rules_string = (f"\n - Each player will vote for one player they want to REMOVE from the game. "
                        f"\n - The player that receives the most votes will leave the game IMMEDIATELY. ")
        if self.cfg().vote_dont_miss:
            rules_string += f"\n - {GamePromptLibrary.dont_miss_string.format(points = self.cfg().vote_missed_points)}"
        return rules_string
        
    def run_vote(self, immunity_players: Optional[Sequence[str]]):
        dont_miss = self.cfg().vote_dont_miss
        self.run_voting_round_basic(immunity_players, dont_miss = dont_miss)
        
              
    def run_voting_round_basic(self, immunity_players: Optional[Sequence[str]] = None, dont_miss: bool = False):
        
        immunity_players = self._validate_immunity(immunity_players)
        if len(self.simulationEngine.agents) <= 2:
            print("WARNING: Only 2 players. Shoudln't run here")
            #maybe run other vote instead
    
        players_up_for_elimination = [a.name for a in self._players_up_for_elimination(immunity_players)]
        host_message = (f"🚨🚨🚨 IT'S TIME TO VOTE. ")
        host_message += VoteEachPlayer.rules_description_detailed(self)             
        host_message += self.immunity_string(immunity_players, players_up_for_elimination )
        
        self.gameBoard.host_broadcast(host_message)
        victim_name, voting_results = self.process_vote_rounds(players_up_for_elimination)
        if dont_miss:
            self._dispense_victim_points(victim_name, voting_results)
        self.eliminate_player_by_name(victim_name)
   
