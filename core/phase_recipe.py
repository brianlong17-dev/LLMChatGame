
from typing import List, Optional, Type
from pydantic import BaseModel

from gameplay_management.base_manager import BaseRound
from gameplay_management.immunities.immunity_mechanicsMixin import ImmunityMechanicsMixin


class PhaseRecipe(BaseModel):
    rounds: List[Type[BaseRound]] = None 
    immunity_types: Optional[List[Type[ImmunityMechanicsMixin]]] = None  # e.g., ["winner_immunity", "public_vote_immunity"]
    overall_game_rules: Optional[str] = None #if not none will be sent to the phase runner for the context builder
    
    def phase_summary_string(self, game_manager):
        round_summary = '\n-----------------\n'
        for round in self.rounds:
            round_summary += f"{round.display_name(game_manager)} - {round.rules_description(game_manager)}\n"
        round_summary += '-----------------\n'
        return round_summary
    
    def phase_progress_string(self, game_manager, current_index):
        round_summary = '\n-----------------\n'
        current_index -= 1 
        for i, round in enumerate(self.rounds):
            if i < current_index:
                status = "COMPLETED"
            elif i == current_index:
                status = "CURRENTLY ONGOING"
            else:
                status = "UPCOMING"
            
            round_summary += f"{round.display_name(game_manager)} - {status}\n"
        round_summary += '-----------------\n'
        round_summary += self.detailed_rules_string(game_manager, current_index)
       
        return round_summary 
    
    def detailed_rules_string(self, game_manager, current_index):
        rules_string = '\n-----------------\n'
        rules_string += '------- UPCOMING GAME RULES ----------\n'
        count = 0
        for i, round in enumerate(self.rounds):
            if i > current_index:
                if round.is_game() or round.is_vote():
                    count += 1
                    rules_string += f"{round.display_name(game_manager)} - {round.rules_description(game_manager)}\n"
        if count == 0:
            return ""
        rules_string += '-----------------\n'
        return rules_string
        
        
    def phase_intro_string(self, phase_number, num_players, game_manager): #game_manager
        #this should not be here
        phase_description = f"🚨 WELCOME PLAYERS, TO PHASE {phase_number} 🚨. "
        
        #TODO this is temp
        
        if num_players == 2:
            phase_description = f"🚨 Only two players remain. Unfortunately only one player can win. Only one player will remain at the end of this phase. The player with the most points. Act accordingly. Accept your fate, or fight 🚨\n"
        
        #--------------------
        
        phase_description += f"In this round we will have: "
        
        discussion_rounds = [round for round in self.rounds if round.is_discussion()]
        if len(discussion_rounds) == 1:
            phase_description += "A discussion round. "
        elif len(discussion_rounds) > 1:
            phase_description += "Discussion rounds. "
            
            
        if any(round.is_game() for round in self.rounds):
            phase_description += "A Game Round. "
            
        has_elimination = any(round.is_vote() for round in self.rounds)
        if has_elimination:
            phase_description += "An Elimination. "
        
        
        if has_elimination and self.immunity_types:
            immunity_message = f"HOWEVER! This elimination round has the following immunities in play:\n"
            for immunity in self.immunity_types:
                immunity_message += f"- {immunity.display_name(game_manager)}: {immunity.rules_description(game_manager)}\n"
            phase_description += immunity_message
        
      
        return phase_description
        
   