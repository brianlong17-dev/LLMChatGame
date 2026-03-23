from collections import deque
from dataclasses import dataclass
from typing import Union
from agents.base_agent import BaseAgent
from core.context_builder import ContextBuilder

@dataclass
class MessageEntry:
    messages: list[dict]  # [{"speaker": name, "message": text}]
    id: int #sequential number, allow you to append / access specific convos
    visibility_restriction: set[str] | None = None  # None = public
    
@dataclass
class RoundEntry:
    phase_number: int
    round_number: int
    messages: list[MessageEntry]
    
class GameBoard:
    def __init__(self,  game_sink):
        self.game_sink = game_sink
        
        self.phase_number = 0
        self.round_number = 0
        self.turn_number = 0 #just for printing...
        
        self.message_id = 0
        
        self.completed_round_entries: list[RoundEntry] = []
        self.current_round: RoundEntry = None #made by new round #RoundEntry(phase_number=0, round_number=0, messages=[])

        
        self.agent_scores: dict[str, int] = {}
        self.context_builder = ContextBuilder(game_board = self)
        
        self.phase_runner = None
    
    def current_phase_rounds(self):
        return self.phase_rounds(self.phase_number)
    
    def phase_rounds(self, phase_number):
        return [r for r in self.completed_round_entries if r.phase_number == phase_number] 
        
    def log_new_restricted_conversation(self, restricted_users, player_name, message):
        return self._update_history(player_name, message, restricted_users)
    
    def log_message_to_conversation(self, conversation_id, player_name: str, message: str):
        entry = self._get_conversation_entry(conversation_id)
        if entry:
            entry.messages.append({"speaker": player_name, "message": message})
    
    def _get_conversation_entry(self, conversation_id):
        entry = next((e for e in self.current_round.messages if e.id == conversation_id), None)
        if not entry:
            print(f"Conversation {conversation_id} not found.")
        return entry
        
    def _update_history(self, player_name, message, visibility_restriction = None):
        #entry = MessageEntry()
        self.message_id += 1
        entry = MessageEntry(
            messages=[{"speaker": player_name, "message": message}],
            id= self.message_id,
            visibility_restriction=visibility_restriction
        )
        self.current_round.messages.append(entry)
        return self.message_id
    
    def output_private_conversation(self, conversation_id):
        entry = self._get_conversation_entry(conversation_id)
        if entry:
            self.game_sink.on_private_conversation(entry)
    
    def get_agent_score(self, agent_name: str) -> int:
        if agent_name not in self.agent_scores:
            raise RuntimeError(f"Missing score for active player '{agent_name}'")
        return self.agent_scores[agent_name]

    ####  ...... Phase, turn management .... #########

    def new_turn_print(self):
        #TODO - what is the point here- ? only on discussion turns? why?
        self.turn_number += 1
        self.game_sink.on_turn_header(self.turn_number)
    
        
    def endRound(self, round_summary):
        self.game_sink.on_round_summary(round_summary.round_summary)
        self.completed_round_entries.append(self.current_round)
        
    def newRound(self):
        #self.system_broadcast(self.score_string(), private = False) Probably a good idea for agents to read
        self.round_number += 1
        self.turn_number = 0
        self.current_round = RoundEntry(phase_number=self.phase_number, round_number=self.round_number, messages=[])
        self.game_sink.on_round_start(self.round_number, self.score_string()) 
        
    def endPhase(self):
        pass
        
    def new_phase(self):
        self.phase_number += 1
        self.game_sink.on_phase_header(self.phase_number) 
        
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
        
        
        
    def broadcast_public_action(self, speaker: Union[str, BaseAgent], message: str, color: str = ""): #broadcast to record
        
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
    
    # ---------------Agent state / Scores --------------------#
    
    def agent_names(self):
        return self.phase_runner.agent_names()
    
    
    def remove_agent_state(self, agent_name: str):
        self.agent_scores.pop(agent_name, None)

    def initialize_agents(self, agent_list):
        for agent in agent_list:
            self.add_agent_state(agent.name)
            
    def add_agent_state(self, agent_name: str):
        self.agent_scores[agent_name] = 0
        
    
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
                
