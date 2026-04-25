from collections import deque
from typing import Union
from agents.base_agent import BaseAgent
from core.context_builder import ContextBuilder
from core.models import MessageEntry, RoundEntry

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
        
        self._current_round_summarisation : str = ""
        self._current_round_summarisation_until : int = None
    
    def push_current_round_summarisation(self, summary: str, last_message_id: int):
        self._current_round_summarisation = summary
        self._current_round_summarisation_until = last_message_id
    
    def most_recent_message_id(self) -> int:
        return self.message_id

    def _is_sys_admin_message(self, message: 'MessageEntry') -> bool:
        return message.visibility_restriction and self.SYS_ADMIN in message.visibility_restriction

    def messages_since(self, message_id: int) -> list['MessageEntry']:
        return [m for m in self.current_round.messages if m.id > message_id and not self._is_sys_admin_message(m)]

    def _current_round_messages_up_to(self, message_id: int) -> list['MessageEntry']:
        return [m for m in self.current_round.messages if m.id <= message_id and not self._is_sys_admin_message(m)]

    def current_phase_rounds(self):
        return self.phase_rounds(self.phase_number)
    
    def phase_rounds(self, phase_number):
        return [r for r in self.completed_round_entries if r.phase_number == phase_number] 
        
    def _human_in_restriction(self, restricted_users):
        if not restricted_users:
            return False
        return any(
            a.is_human() and a.name in restricted_users
            for a in self.phase_runner.simulation_engine.agents
        )

    def log_new_restricted_conversation(self, restricted_users, player_name, message):
        
        if self._human_in_restriction(restricted_users):
            header = f"[Private: {' & '.join(restricted_users)}]"
            self.game_sink.system_private(header)
            self.game_sink.on_public_action(player_name, message, "RED")
        return self._update_history(player_name, message, restricted_users)

    def log_message_to_conversation(self, conversation_id, player_name: str, message: str):
        entry = self._get_conversation_entry(conversation_id)
        if entry:
            entry.messages.append({"speaker": player_name, "message": message})
            if self._human_in_restriction(entry.visibility_restriction):
                self.game_sink.on_public_action(player_name, message, "RED")
    
    def _get_conversation_entry(self, conversation_id):
        entry = next((e for e in self.current_round.messages if e.id == conversation_id), None)
        if not entry:
            self.game_sink.on_warning(f"Conversation {conversation_id} not found.")
        return entry
        
    def _update_history(self, player_name, message, visibility_restriction = None):
        #entry = MessageEntry()
        self.message_id += 1
        entry = MessageEntry(
            messages=[{"speaker": player_name, "message": message}],
            id= self.message_id,
            visibility_restriction=visibility_restriction
        )
        #if visibility restriction includes human player- the we need to print it
        self.current_round.messages.append(entry)
        return self.message_id
    
    def close_private_conversation(self, conversation_id, silent = False):
        entry = self._get_conversation_entry(conversation_id)
        if entry:
            #entry.messages.append({"speaker": "SYSTEM", "message": "[End Private]"})
            if not self._human_in_restriction(entry.visibility_restriction):
                #if human involve wave already outputted
                if not silent:
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
        self._current_round_summarisation = ""
        self._current_round_summarisation_until = None
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
    
    def handle_public_private_output(self, agent: BaseAgent, response,  delay: float = 0.0, output_inner_workings = False):
        public_message, private_message = response.public_response, response.private_thoughts
        other_fields = []
        self.broadcast_public_action(agent, public_message)
        self.game_sink.on_private_thought(agent, private_message)
        if output_inner_workings:
            self.game_sink.on_inner_workings(agent, self._get_inner_thought_fields(response))
        self.game_sink.delay(delay)
        
        
        
    def broadcast_public_action(self, speaker: Union[str, BaseAgent], message: str, color: str = ""): #broadcast to record
        
        display_name = self._as_display_name(speaker)
        self._update_history(display_name, message)
        self.game_sink.on_public_action(speaker, message)
    
    def system_broadcast(self, message, private = False):
        if private:
            self.game_sink.system_private(message)
        else:
            self.broadcast_public_action("SYSTEM", message)
        
    def host_broadcast(self, message, delay: float = 0.0):
        self.broadcast_public_action("HOST", message)
        if delay:
            self.game_sink.delay(delay)
            
    def environment_broadcast(self, message, delay):
        #TODO make this right
        #its kind of BANG BANG-
        #Maybe the lights go out- is another one
        self.broadcast_public_action("", message)
        if delay:
            self.game_sink.delay(delay)
    
    # ---------------Agent state / Scores --------------------#
    
    def agent_names(self):
        return self.phase_runner.agent_names()
    
    
    def remove_agent_state(self, agent_name: str):
        self.agent_scores.pop(agent_name, None)
        self.game_sink.on_points_update(self.agent_scores)
        self.game_sink.on_evictions_update(self.phase_runner.removed_agent_names())
        

    SYS_ADMIN = "SYS_ADMIN"
    RESERVED_NAMES = {"HOST", "SYSTEM", SYS_ADMIN}

    def _unique_name(self, name: str, existing: set[str]) -> str:
        candidate = name
        if candidate.upper() in self.RESERVED_NAMES or candidate in existing:
            i = 1
            while f"{name}_{i}" in existing:
                i += 1
            candidate = f"{name}_{i}"
        return candidate

    def initialize_agents(self, agent_list):
        seen = set()
        for agent in agent_list:
            agent.name = self._unique_name(agent.name, seen)
            seen.add(agent.name)
            self.add_agent_state(agent.name)
            self.game_sink.on_points_update(self.agent_scores)
        
            
    def add_agent_state(self, agent_name: str):
        self.agent_scores[agent_name] = 0
        
    
    def append_agent_points(self, agent_name, points):
        new_score = max(0, self.agent_scores[agent_name] + points)
        self.agent_scores[agent_name] = new_score
        self.game_sink.on_points_update(dict(self.agent_scores))

    def score_string(self) -> str:
        sorted_scores = sorted(self.agent_scores.items(), key=lambda item: item[1], reverse=True)
        return ", ".join(f"{name}: {score}" for name, score in sorted_scores)
             
                
