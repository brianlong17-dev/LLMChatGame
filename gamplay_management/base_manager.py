from collections import Counter
import random
import re

from core.gameboard import ConsoleRenderer
from agents.base_agent import BaseAgent

   
        
class BaseManager:
    def __init__(self, gameBoard, simulationEngine):
        self.gameBoard = gameBoard
        self.simulationEngine = simulationEngine
        
    def publicPrivateResponse(self, agent: BaseAgent, result):
        public_message, private_message = result.public_response, result.private_thoughts
        self.gameBoard.broadcast_public_action(agent, public_message)
        #TODO send thru gameboard- future proofing turning on/off - lives in a setting, the printer has no state
        ConsoleRenderer.print_private(agent, f"{private_message}\n", print_name = False)
        #self.process_magic_words(agent, public_message)
    
    def _output_discussion_round_text(self, player, result):
        public_text = result.public_response
        if getattr(result, "public_action", None):
            public_text = f"[{result.public_action}]\n {public_text}"
            
        self.gameBoard.broadcast_public_action(player, public_text)
        
        turn_dict = result.model_dump()
        fields_to_exclude = {"public_response", "public_action"}
        for key, value in turn_dict.items():
            if key not in fields_to_exclude:
                # Optional: capitalize or format the key so it looks nicer in the console
                formatted_key = key.replace('_', ' ').title() 
                message = f"{formatted_key} : {value}"
                ConsoleRenderer.print_private(player, message, print_name=False)
    
    def run_discussion_round(self):
        for player in self.simulationEngine.agents:
            if not self.gameBoard.agent_response_allowed.get(player.name, True):
                continue #this is almost redundant because the judge is almost gone.

            result = player.make_discussion_turn(self.gameBoard)
            self.gameBoard.new_turn_print()
            self._output_discussion_round_text(player, result)
        
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
    
    def _names(self, agents):
        return [agent.name for agent in agents]
    
    def _agent_by_name(self, name):
        return next((agent for agent in self.simulationEngine.agents if agent.name == name), None)
    
    def get_strategic_player(self, available_agents, top_player = True):
        """
        Selects a player from available_agents based on rank.
        mode="top": Picks from the leaders.
        mode="bottom": Picks from the tail-enders.
        """
        agent_names = self._names(available_agents)
        current_scores = {name: score for name, score in self.gameBoard.agent_scores.items() 
                        if name in agent_names}
        # Guard against empty lists
        if not current_scores:
            return None
        if top_player:
            target_score = max(current_scores.values())
        else:
            target_score = min(current_scores.values())
            
        eligible_players = [name for name, points in current_scores.items() if points == target_score]
        selected_player = random.choice(eligible_players)
        return self._agent_by_name(selected_player)

    def _handle_manual_pairing(self, available_agents, winner_picks_first = True):
        """Helper to manage the 'choice' logic for a single pair."""
        available_agents_names = [a.name for a in available_agents]
        chooser = self.get_strategic_player(available_agents, winner_picks_first) 
        available_agents.remove(chooser)
        
        response = chooser.choose_partner(self.gameBoard, available_agents_names)
        partner = self._agent_by_name(response.action)
        
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
    
 
  
