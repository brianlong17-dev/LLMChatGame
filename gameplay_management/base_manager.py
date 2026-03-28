from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import random
import time
from typing import Callable, Literal, Sequence
from pydantic import Field
from agents.base_agent import BaseAgent
from models.player_models import DynamicModelFactory
from prompts.prompts import PromptLibrary
from prompts.gamePrompts import GamePromptLibrary
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # 2. This is only imported during static analysis (linting)
    from agents.player import Debater

   
        
class BaseRound: #base class
    def __init__(self, gameBoard, simulationEngine):
        self.gameBoard = gameBoard
        self.simulationEngine = simulationEngine
    
    def publicPrivateResponse(self, agent: BaseAgent, result, delay: float = 0.0, action_string = ""):
        #TODO depreciate
        self.gameBoard.handle_public_private_output(agent, result, delay)
    
    @classmethod
    def is_discussion(cls):
        return False
    
    @classmethod
    def is_game(cls):
        return False
    
    @classmethod
    def is_vote(cls):
        return False
    
    def _run_tasks(
        self,
        tasks: list[tuple], #list of argue
        worker: Callable[..., tuple],
        parallel: bool = True,
    ) -> list[tuple]:
        if not tasks:
            return []
        if parallel:
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(worker, *task) for task in tasks]
                return [f.result() for f in futures]
        return [worker(*task) for task in tasks]

    
    
    
    
    def _names(self, agents: Sequence["Debater"]) -> list[str]:
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
    
    def create_basic_field(self, field_name, field_description):
        field_definition = (str, Field(description=field_description))
        return {field_name: field_definition}
    
    def _choose_name_field(self, allowed_names, reason_for_choosing_prompt):
        choice_reason_prompt = f"The exact name of the agent. {reason_for_choosing_prompt}"
        return self.create_choice_field(GamePromptLibrary.model_field_choose_name, allowed_names, choice_reason_prompt)

    def _make_player_turn(self, player: Debater, user_prompt: str, response_model, action_fields=None):
        
        return player.take_turn_standard(user_prompt, self.gameBoard, response_model)
        
    def get_response(self, player, model_name, context_msg, action_fields= None, additional_thought_nudge = None):
        model = DynamicModelFactory.create_model_(
            player,
            model_name,  
            additional_thought_nudge=additional_thought_nudge, 
            action_fields=action_fields
        )
        return player.take_turn_standard(context_msg, self.gameBoard, model)
    
    def cfg(self):
        return self.simulationEngine.gameplay_config
    
    def format_list(self, lst):
        if not lst:
            return ""
        if len(lst) == 1:
            return str(lst[0])
        
        # Joins all but the last with a comma, then adds the final "and"
        return ", ".join(map(str, lst[:-1])) + " and " + str(lst[-1])
