from collections import Counter
from typing import Sequence
from gameplay_management.base_manager import *

class VotingRoundBase(BaseRound):
    dont_miss_string = "A player that receives votes but is not eliminated will receive {points} points per failed vote. "

    def __init__(self, game_board, simulationEngine):
        super().__init__(game_board, simulationEngine)

    def _human_survivor_description(self):
        return self._human_result_description("You survived. What do you say?", "...")
    
    ###############
    #   Helper    #
    ###############
    
    @classmethod
    def is_vote(cls):
        return True
    
    
       
    def _facing_the_vote_string(self, players_up_for_elimination: Sequence[str]):
        players_up_for_elimination_string = (
            f"\nThe following players are up for elimination:\n *{self.format_list(players_up_for_elimination)}*"
        )
        return players_up_for_elimination_string
    
    
            
        
    ###############
    #   Logic     #
    ###############
    
    def _handle_vote_response(self, agent, vote_response):
        actual_vote = self.turn_manager._get_target_name_from_response(vote_response)
        widget = self._build_voting_widget_update(agent.name, actual_vote or "—")
        self.turn_manager._output_response(agent, vote_response, is_reply=True, pre_message_choice_reveal=self.TARGET_NAME_FIELD,
                                           widget=widget)
        return actual_vote
        
