from collections import deque
import time
from typing import Union
from agents.base_agent import BaseAgent
from core.context_builder import ContextBuilder

class GameBoard:
    def __init__(self, game_master, game_sink):
        self.game_sink = game_sink
        
        self.game_master = game_master
        
        self.full_rounds_text_amount = 3 #we get current round and past round
        self.agent_names = []
        self.round_number = 0
        self.turn_number = 0
        self.phase_number = 0
        self.current_phase_round_number = 0
        
        self.execution_style = False
        
        self.history = []
        self.currentRound = []
        self.current_phase_rounds = []
        
        self.round_entries = deque(maxlen=10)#dont rly need
        self.round_summaries = deque(maxlen=50)
        self.agent_scores: dict[str, int] = {}
        self.agent_response_allowed: dict[str, bool] = {}
        self.removed_agent_names = []
        self.overall_game_rules = ""
        self.context_builder = ContextBuilder(game_board = self)
        self.has_human_player = False #this is for some printing differences
        self.testing_prompts = False
        self.current_phase_recipe = None
        
        self.phase_progress_string = ""
    
    def get_agent_score(self, agent_name: str) -> int:
        if agent_name not in self.agent_scores:
            raise RuntimeError(f"Missing score for active player '{agent_name}'")
        return self.agent_scores[agent_name]


    def new_turn_print(self):
        #TODO - what is the point here- ? only on discussion turns? why?
        self.turn_number += 1
        self.game_sink.on_turn_header(self.turn_number)
    
    def endRound(self):
        roundSummary = self.game_master.summariseRound(self)
        print("round summary: ")
        print(roundSummary)
        self.round_summaries.append(roundSummary.round_summary)
        self.game_sink.on_round_summary(roundSummary.round_summary)
        self.round_entries.append(list(self.currentRound))
        self.current_phase_rounds.append(list(self.currentRound))
        self.currentRound.clear()
        
        
    def newRound(self):
        #self.system_broadcast(self.score_string(), private = False)
        
        self.round_number += 1
        self.current_phase_round_number += 1
        self.turn_number = 0
        self.game_sink.on_round_start(self.round_number, self.score_string()) #TODO with string
        
    def endPhase(self):
        #should get phase summaries here
        self.current_phase_round_number = 0
        
        pass
    
        
    def new_phase(self, recipe, game_manager ):#this can be removed when games become stateless
        
        self.phase_number += 1
        host_intro = recipe.phase_intro_string(self.phase_number, len(self.agent_names), game_manager)
        system_phase_summary = recipe.phase_summary_string(game_manager)
        
        self.current_phase_rounds = []
        self.game_sink.on_phase_header(self.phase_number) 
        self.host_broadcast(host_intro)

        self.system_broadcast( system_phase_summary, private = True) #these need their own thing, like an invisible sys print
        
        
    #--------- public output --------- #
    def _as_display_name(self, speaker: Union[str, BaseAgent]):
        if isinstance(speaker, str):
            display_name = speaker
        else:
            display_name = speaker.name
        return display_name
    
    def _get_inner_thought_fields(self, response):
        result_dict = response.model_dump()      
        #TODO these shouldn't be hard coded, but anyway
        excluded_keys = {"public_response", "private_thoughts"}
        other_fields = [
            (key, value) for key, value in result_dict.items() 
            if key not in excluded_keys
        ]
        return other_fields
    
    def handle_public_private_output(self, agent: BaseAgent, response,  delay: float = 0.0, override = False):
        public_message, private_message = response.public_response, response.private_thoughts
        other_fields = []
        self.broadcast_public_action(agent, public_message)
        self.game_sink.on_private_thought(agent, private_message)
        self.game_sink.on_inner_workings(agent, self._get_inner_thought_fields(response), override=override)
        self.game_sink.delay(delay)
        
        
        
    def broadcast_public_action(self, speaker: Union[str, BaseAgent], message: str, color: str = ""):
        
        display_name = self._as_display_name(speaker)
        self._update_history(display_name, message)
        self.game_sink.on_public_action(speaker, message)
    
    def system_broadcast(self, message, private = False):
        if private:
            self.game_sink.system_private("SYSTEM", message)
        else:
            self.broadcast_public_action("SYSTEM", message)
        
    def host_broadcast(self, message):
        self.broadcast_public_action("HOST", message)
    
    # -----------------------------------#
        
    def remove_agent_state(self, agent_name: str):
        """Cleans up the dictionaries when an agent dies."""
        self.removed_agent_names.append(agent_name)
        self.agent_names.remove(agent_name)
        self.agent_scores.pop(agent_name, None)
        self.agent_response_allowed.pop(agent_name, None)

    def initialize_agents(self, agent_list):
        for agent in agent_list:
            self.add_agent_state(agent.name, 0)
            
    def add_agent_state(self, agent_name: str, initial_score: int = None):
        """Initializes dictionaries for a newly born agent."""
        self.agent_names.append(agent_name)
        #adding a new player midway gets average points. Redundant TODO remove 
        if initial_score == None:
            current_scores = list(self.agent_scores.values())
            initial_score = int(sum(current_scores) / len(current_scores)) if current_scores else 0
        self.agent_scores[agent_name] = initial_score
        self.agent_response_allowed[agent_name] = True  
        
    def _update_history(self, player_name, message):
        entry = {"speaker": player_name, "message": message}
        self.currentRound.append(entry)
    
    def append_agent_points(self, agent_name, points):
        new_score = max(0, self.agent_scores[agent_name] + points)
        self.agent_scores[agent_name] = new_score
        self.game_sink.on_points_update(dict(self.agent_scores))

    def score_string(self) -> str:
        sorted_scores = sorted(self.agent_scores.items(), key=lambda item: item[1], reverse=True)
        return ", ".join(f"{name}: {score}" for name, score in sorted_scores)
             
    def resetScores(self):
        for entry in self.agent_scores:
            self.agent_scores[entry] = 0
        self.game_sink.on_points_update(dict(self.agent_scores))
                
