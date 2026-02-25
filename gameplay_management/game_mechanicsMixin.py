from pydantic import Field
from gameplay_management.base_manager import BaseManager
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
import random
from typing import TYPE_CHECKING, Dict, Literal

if TYPE_CHECKING:
    from agents.player import Debater

class GameMechanicsMixin(BaseManager):
    
    def _generate_pairings(self, agents, choose_partner, winner_picks_first = True):
        """Pairs agents and returns a list of tuples and the leftover agent."""
        pairs = []
        # Work on a copy if you don't want to mutate the original list
        available = agents[:] 
        
        while len(available) >= 2:
            if choose_partner:
                pair = self._handle_manual_pairing(available, winner_picks_first)
            else:
                pair = (available.pop(), available.pop())
                
            if pair:
                pairs.append(pair)

        leftover = available[0] if available else None
        return pairs, leftover
    
    def _handle_manual_pairing(self, available_agents, winner_picks_first = True):
        """Helper to manage the 'choice' logic for a single pair."""
        
        chooser = self.get_strategic_player(available_agents, winner_picks_first) 
        available_agents.remove(chooser)
        
        available_agents_names = [a.name for a in available_agents]
        user_content = (
            f"You get to choose who you want to play with from the following list: {available_agents_names}.\n"
            f"Based on your history and the current game context, who do you choose to partner up with for the next mini-game and why?"
        )
        name_field_prompt = "The exact name of the agent to PAIR UP WITH.."
        
        #----------------------
        action_fields = self._choose_name_field(available_agents_names, name_field_prompt) 
        response_model = DynamicModelFactory.create_model_(chooser, model_name="PickPartner", action_fields=action_fields) 
        response = chooser.take_turn_standard(user_content, self.gameBoard, response_model)
        partner = self._agent_by_name(response.action)
        #-----------------------
        self.publicPrivateResponse(chooser, response)

        if partner in available_agents:
            available_agents.remove(partner)
            msg = f"{chooser.name} has chosen to partner with {partner.name}!"
        else:
            # Fallback to random if choice is invalid or None
            partner = available_agents.pop()
            msg = f"{chooser.name} has been randomly paired with {partner.name}!"

        self.gameBoard.host_broadcast(msg)
        #I guess they could both react here
        return (chooser, partner)
    
