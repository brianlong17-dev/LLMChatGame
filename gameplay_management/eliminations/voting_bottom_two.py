from typing import Optional, Sequence
from pydantic import Field, create_model
from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from prompts.gamePrompts import GamePromptLibrary

class VoteBottomTwo(VoteMechanicsMixin):
     
    def display_name(self):
        return "Bottom Two"

    def rules_description(self):
        return "The bottom two players will face the vote to be removed."
        
        
    def rules_description_detailed(self):
        rules_string = VoteBottomTwo.rules_description(self)
        if self.cfg().vote_bottom_two_multiple:
            rules_string += "In the event of a tie for the bottom spots, all tied players will also face the vote. "
        if self.cfg().vote_dont_miss:
            rules_string += GamePromptLibrary.dont_miss_string.format(points = self.cfg().vote_missed_points)
            
        return rules_string
        
            
    def run_vote(self, immunity_players: Optional[Sequence[str]]):
        self.run_voting_bottom_players(immunity_players, multiple = self.cfg().vote_bottom_two_multiple,
                                       dont_miss = self.cfg().vote_dont_miss)
    
     
    
    def run_voting_bottom_players(self, immunity_players: Optional[Sequence[str]] = None, dont_miss: bool = True, multiple: bool = False, count: int = 2):
    
        players_up_for_elimination = self._players_up_for_elimination(immunity_players)
        if len(players_up_for_elimination) < 2:
            print("Not enough players!")
            return
        
        immunity_players = self._validate_immunity(immunity_players)
        players_up_for_elimination = self.get_bottom_players(players_up_for_elimination, min = 2, multiple=multiple)
        
        host_intro_msg = (self.rules_description_detailed())
        host_intro_msg += self.immunity_string(immunity_players, 
                                               self._names(players_up_for_elimination))
        self.gameBoard.host_broadcast(host_intro_msg)
        
        
        victim_name, voting_results = self.process_vote_rounds(self._names(players_up_for_elimination))
        if dont_miss:
            self._dispense_victim_points(victim_name, voting_results)
        self.eliminate_player_by_name(victim_name)
     
     
     
    def get_bottom_players(self, players_up_for_elimination, min = 2, multiple = False):
        selected_players = []
        pool = list(players_up_for_elimination)
        while len(selected_players) < min and pool:
            batch = self.get_strategic_players(pool, top_player = False, multiple = multiple)
            if not batch:
                break
            selected_players.extend(batch)
            pool = [p for p in pool if p not in selected_players]
        return selected_players
    
