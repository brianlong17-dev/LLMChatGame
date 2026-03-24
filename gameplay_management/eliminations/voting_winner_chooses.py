from typing import Optional, Sequence

from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.votePrompts import VotePromptLibrary


class VoteWinnerChooses(VoteMechanicsMixin):
    @classmethod
    def display_name(cls, cfg):
        return "The Leader Executes"

    @classmethod
    def rules_description(cls, cfg):
        return "The player leading the scores will choose who leaves the game IMMEDIATELY."

    def run_vote(self, immunity_players: Optional[Sequence[str]]):
        self.run_voting_winner_chooses(immunity_players)
    
    def _get_winner_chooses_model(self, leading_player, up_for_elimination):
        
        choice_prompt = VotePromptLibrary.winner_chooses_choice_prompt
        additional_thought_nudge = VotePromptLibrary.winner_chooses_thought_nudge
        #--------------
        
        action_fields = self.create_choice_field("target_name", up_for_elimination, field_description= choice_prompt)
        return DynamicModelFactory.create_model_(leading_player, "leader_vote_player_off", 
                    additional_thought_nudge=additional_thought_nudge, action_fields=action_fields)
        
        
    def run_voting_winner_chooses(self, immunity_players: Optional[Sequence[str]] = None, with_pass_option: bool = False):
        
        leading_player= self.get_strategic_players(self.simulationEngine.agents, top_player = True)[0]
        immunity_players = self._validate_immunity(immunity_players)
        up_for_elimination = [
            name for name in self.gameBoard.agent_names()
            if name != leading_player.name and name not in immunity_players
        ]
        
        if not up_for_elimination:
            self.gameBoard.host_broadcast("No players qualify for elimination! Everyone is safe")
            return
            
                
        leading_player_message = VotePromptLibrary.winner_chooses_host_msg.format(
            leading_player_name=leading_player.name,
            other_agent_names=", ".join(up_for_elimination),
        )

        self.gameBoard.host_broadcast(leading_player_message)
        
        
        model = self._get_winner_chooses_model(leading_player, up_for_elimination)
        context_msg = VotePromptLibrary.winner_chooses_context_msg
        response = leading_player.take_turn_standard(context_msg, self.gameBoard, model)
        #-------------
        
        self.publicPrivateResponse(leading_player, response)
        self.eliminate_player_by_name(response.target_name)
