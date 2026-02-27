from __future__ import annotations
import random
import time
from typing import Literal
from pydantic import Field
from core.gameboard import ConsoleRenderer
from agents.base_agent import BaseAgent
from models.player_models import DynamicModelFactory
from prompts.prompts import PromptLibrary
from prompts.gamePrompts import GamePromptLibrary
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # 2. This is only imported during static analysis (linting)
    from agents.player import Debater

   
        
class BaseManager: #base class
    def __init__(self, gameBoard, simulationEngine):
        self.gameBoard = gameBoard
        self.simulationEngine = simulationEngine
        
    def publicPrivateResponse(self, agent: BaseAgent, result, delay: float = 0.0):
        public_message, private_message = result.public_response, result.private_thoughts
        self.gameBoard.broadcast_public_action(agent, public_message)
        #TODO send thru gameboard- future proofing turning on/off - lives in a setting, the printer has no state
        ConsoleRenderer.print_private(agent, f"{private_message}\n", print_name = False)
        time.sleep(delay)#only when you're thead pooling!
       
    
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
            #-----------
            user_content =  "Time to discuss!"
            basic_model = DynamicModelFactory.create_model_(player, "basic_turn")
            result = player.take_turn_standard(user_content, self.gameBoard, basic_model)
            #----------
            self.gameBoard.new_turn_print()
            self._output_discussion_round_text(player, result)
        
    
    
    def _names(self, agents):
        return [agent.name for agent in agents]
    
    def _agent_by_name(self, name):
        return next((agent for agent in self.simulationEngine.agents if agent.name == name), None)
    
    def get_strategic_players(self, available_agents, top_player = True, multiple = False) -> list[Debater]:
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
            return []
        if top_player:
            target_score = max(current_scores.values())
        else:
            target_score = min(current_scores.values())
            
        eligible_players = [name for name, points in current_scores.items() if points == target_score]
        random.shuffle(eligible_players)
        if multiple: 
            return [self._agent_by_name(p) for p in eligible_players]
        else: 
            return [self._agent_by_name(eligible_players[0])]

    
    def _shuffled_agents(self):
        agents = list(self.simulationEngine.agents)
        return random.sample(agents, k=len(agents))
    
    def respond_to(self, player: Debater, text_to_respond_to: str, public_response_prompt: str = None, private_thoughts_prompt: str =None, instruction_override= None):
        
        model = DynamicModelFactory.create_model_(player, public_response_prompt = public_response_prompt, 
                                                     private_thoughts_prompt = private_thoughts_prompt)
        return player.take_turn_standard(text_to_respond_to, self.gameBoard, model, instruction_override=instruction_override)
    
    def create_choice_field(self, field_name, choices, field_description= None):
        if not field_description:
            field_description = "Your final choice."
        choice_definition = (Literal[*choices], Field(description=field_description))
        return {field_name: choice_definition}
    
    def _choose_name_field(self, allowed_names, reason_for_choosing_prompt):
        choice_reason_prompt = f"The exact name of the agent. {reason_for_choosing_prompt}"
        return self.create_choice_field(GamePromptLibrary.model_field_choose_name, allowed_names, choice_reason_prompt)

    def _make_player_turn(self, player: Debater, user_prompt: str, response_model, action_fields=None):
        
        return player.take_turn_standard(user_prompt, self.gameBoard, response_model)
        
    def get_response(self, player, model_name, context_msg, action_fields= None, additional_thought_nudge = None):
        model = model = DynamicModelFactory.create_model_(
            player,
            model_name,  
            additional_thought_nudge=additional_thought_nudge, 
            action_fields=action_fields
        )
        return player.take_turn_standard(context_msg, self.gameBoard, model)