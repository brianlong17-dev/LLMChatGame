from typing import Union
from agents.base_agent import BaseAgent
from core.game_context.context_builder import ContextBuilder
from core.game_context.game_log import GameLog
from core.models import RoundEntry


class GameBoard:
    SYS_ADMIN = "SYS_ADMIN"
    HOST_NAME = "HOST"
    SYSTEM = "SYSTEM"
    RESERVED_NAMES = {SYSTEM, SYS_ADMIN, HOST_NAME}

    def __init__(self, game_sink):
        self.game_sink = game_sink
        self.game_log = GameLog()

        self.phase_number = 0
        self.round_number = 0
        self.turn_number = 0

        self.agent_scores: dict[str, int] = {}
        self.context_builder = ContextBuilder(game_board=self, game_log=self.game_log)

        self.phase_runner = None


    def _human_in_restriction(self, restricted_users):
        if not restricted_users:
            return False
        return any(
            a.is_human() and a.name in restricted_users
            for a in self.phase_runner.simulation_engine.agents
        )

    def log_new_restricted_conversation(self, restricted_users, player_name, message):
        if self._human_in_restriction(restricted_users):
            #TODO
            #self.game_sink._on_user_private_conversation(restricted_users, player_name, message, new = True)
            ##
            # web we need to implement , we can no-op for now
            ##
            #this goes to the game_sink console. 
            header = f"[Private: {' & '.join(restricted_users)}]"
            self.game_sink.system_private(header)
            self.game_sink.on_public_action(player_name, message, "RED")
            #####
        return self.game_log._update_history(player_name, message, restricted_users)

    def log_message_to_conversation(self, conversation_id, player_name: str, message: str):
        entry = self._get_conversation_entry(conversation_id)
        if entry:
            entry.messages.append({"speaker": player_name, "message": message})
            if self._human_in_restriction(entry.visibility_restriction):
                #TODO
                #if a human involved - we need to print it! normal - do we need a header?
                #self.game_sink._on_user_private_conversation(restricted_users, player_name, message)
                #same can go into console sink, no-op on web
                self.game_sink.on_public_action(player_name, message, "RED")

    def _get_conversation_entry(self, conversation_id):
        entry = self.game_log._get_conversation_entry(conversation_id)
        if not entry:
            self.game_sink.on_warning(f"Conversation {conversation_id} not found.")
        return entry

    def close_private_conversation(self, conversation_id, silent=False):
        entry = self._get_conversation_entry(conversation_id)
        if entry:
            entry.closed = True
            if not self._human_in_restriction(entry.visibility_restriction):
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
        self.game_log.close_round()

    def newRound(self):
        #self.system_broadcast(self.score_string(), private = False) Probably a good idea for agents to read
        self.round_number += 1
        self.turn_number = 0
        self.game_log.start_round(self.phase_number, self.round_number)
        self.game_sink.on_round_start(self.round_number, self.score_string())

    def endPhase(self):
        pass

    def new_phase(self):
        self.phase_number += 1
        self.game_sink.on_phase_header(self.phase_number)

    #--------- public output --------- #

    def _loading_string(self, string):
        self.game_sink.loading_string(string)

    def _end_loading(self):
        self.game_sink.end_loading()

    def _as_display_name(self, speaker: Union[str, BaseAgent]):
        if isinstance(speaker, str):
            return speaker
        return speaker.name

    def _get_inner_thought_fields(self, response):
        result_dict = response.model_dump()
        #TODO these shouldn't be hard coded, but anyway
        excluded_keys = {"public_response", "private_thoughts"}
        return [
            (key, value) for key, value in result_dict.items()
            if key not in excluded_keys
        ]

    def handle_public_private_output(self, agent: BaseAgent, response, delay: float = 0.0, output_inner_workings=False, 
                                     directed_to_name = None, is_reply: bool = False, pre_string = None):

        if self.game_log._current_round_most_recent_player_entry(self.RESERVED_NAMES) and not agent.is_human():
            self.game_sink.await_continue()
        public_message, private_message = response.public_response, response.private_thoughts
        if pre_string:
            public_message = f"{pre_string}\n{public_message}"


        self.broadcast_public_action(agent, public_message, directed_to_name=directed_to_name, is_reply=is_reply)
        self.game_sink.on_private_thought(agent, private_message)
        if output_inner_workings:
            self.game_sink.on_inner_workings(agent, self._get_inner_thought_fields(response))
        self.game_sink.delay(delay)

    def _should_animate(self, speaker):
        is_system_speaker = speaker in ("SYSTEM", "")
        is_human_speaker = hasattr(speaker, 'is_human') and speaker.is_human()
        return not (is_system_speaker or is_human_speaker)

    def broadcast_public_action(self, speaker: Union[str, BaseAgent], message: str, color: str = "", directed_to_name = None, is_reply = False):
        display_name = self._as_display_name(speaker)
        self.game_log._update_history(display_name, message)
        animate = self._should_animate(speaker)
        self.game_sink.on_public_action(speaker, message, color=color, animate=animate, directed_to_name = directed_to_name, is_reply = is_reply)

    def system_broadcast(self, message, private=False):
        if private:
            self.game_sink.system_private(message)
        else:
            self.broadcast_public_action("SYSTEM", message)

    def _is_sys_host_message(self, message_entry):
        if len(message_entry.messages) == 1:
            msg = message_entry.messages[0]
            return msg.get('speaker') in self.RESERVED_NAMES
        return False
        
    def host_broadcast(self, message, delay: float = 0.0, is_reply: bool = False):
        entry = self.game_log._current_round_most_recent_message_entry()
        if entry and not self._is_sys_host_message(entry):
            self.game_sink.await_continue()
        self.broadcast_public_action(self.HOST_NAME, message, is_reply=is_reply)
        self.game_sink.delay(delay)

    def environment_broadcast(self, message, delay):
        #TODO make this right
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
        self.game_sink.on_cast([a.name for a in agent_list])

    def add_agent_state(self, agent_name: str):
        self.agent_scores[agent_name] = 0

    def append_agent_points(self, agent_name, points):
        #NOTE - this should always come AFTER a player broadcast
        #Because state updates like score are held until after the player output
        #finishes animating on web.
        new_score = max(0, self.agent_scores[agent_name] + points)
        self.agent_scores[agent_name] = new_score
        self.game_sink.on_points_update(dict(self.agent_scores))

    def score_string(self) -> str:
        sorted_scores = sorted(self.agent_scores.items(), key=lambda item: item[1], reverse=True)
        return ", ".join(f"{name}: {score}" for name, score in sorted_scores)
