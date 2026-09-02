from typing import Union
from agents.base_agent import BaseAgent
from core.game_context.context_builder import ContextBuilder
from core.game_context.game_log import GameLog
from core.game_context.models import MessageEntry, RoundBlock


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
        self.round_type = None
        self.round_name = None

        self.agent_scores: dict[str, int] = {}
        self.context_builder = ContextBuilder(game_board=self, game_log=self.game_log)

        self.phase_runner = None
        
        self.game_over = False
        self.score_changed_in_round = False
        self.scores_at_round_start: dict[str, int] = {}
        self.is_typing_array = []
        
        self.first_message_sent = False

    @property
    def mobile_outputs(self) -> bool:
        return getattr(self.game_sink, 'mobile_outputs', False)

    @property
    def auto_run(self) -> bool:
        return getattr(self.game_sink, 'auto_run', False)

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
        return self.game_log._update_history(player_name, message, visibility_restriction=restricted_users)

    def log_message_to_conversation(self, conversation_id, speaker: Union[str, BaseAgent], message: str):
        player_name = self._as_display_name(speaker)
        message_block = self._get_conversation_entry(conversation_id)
        if message_block:
            message_block.message_entries.append(MessageEntry(speaker=player_name, public_output=message))
            if not isinstance(speaker, str):
                speaker.last_message_id = (message_block.id, len(message_block.message_entries) - 1)
            if self._human_in_restriction(message_block.visibility_restriction):
                #TODO
                #if a human involved - we need to print it! normal - do we need a header?
                #self.game_sink._on_user_private_conversation(restricted_users, player_name, message)
                #same can go into console sink, no-op on web
                self.game_sink.on_public_action(player_name, message, "RED")

    def _get_conversation_entry(self, conversation_id):
        message_block = self.game_log._get_conversation_entry(conversation_id)
        if not message_block:
            self.game_sink.on_warning(f"Conversation {conversation_id} not found.")
        return message_block

    def close_private_conversation(self, conversation_id, silent=False):
        message_block = self._get_conversation_entry(conversation_id)
        if message_block:
            message_block.closed = True
            if not self._human_in_restriction(message_block.visibility_restriction):
                if not silent:
                    self.game_sink.on_private_conversation(message_block)
                
    def get_agent_score(self, agent_name: str) -> int:
        if agent_name not in self.agent_scores:
            raise RuntimeError(f"Missing score for active player '{agent_name}'")
        return self.agent_scores[agent_name]

    ####  ...... Phase, turn management .... #########

    def endRound(self, round_summary):
        if round_summary:
            self.game_sink.on_round_summary(round_summary.round_summary)
        self.game_log.close_round()

    def newRound(self, round_type, round_name):
        #self.system_broadcast(self.score_string(), private = False) Probably a good idea for agents to read
        self.round_number += 1
        self.round_type = round_type
        self.round_name = round_name
        self.score_changed_in_round = False
        self.scores_at_round_start = dict(self.agent_scores)
        self.game_log.start_round(self.phase_number, self.round_number, self.phase_runner.current_round_index)
        self.game_sink.on_round_start(self.round_number, round_type, round_name, self.score_string())

    def endPhase(self):
        pass

    def new_phase(self):
        self.phase_number += 1
        self.game_sink.on_phase_header(self.phase_number)

    #--------- public output --------- #

    def _loading_string(self, string):
        self.game_sink.loading_string(string)

    def _end_loading(self, message: str = None):
        self.game_sink.end_loading(message)

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

    def handle_public_private_output(self, agent: BaseAgent, public_resonse, private_thought, private_thought_brief,
            delay: float = 0.0, is_reply: bool = False, directed_to_name=None, widget=None):
        message_id = self.broadcast_public_action_agent(agent, public_resonse, private_thought_brief=private_thought_brief,
                                     directed_to_name=directed_to_name, is_reply=is_reply, widget=widget)

        agent.last_message_id = (message_id, 0)

        if private_thought:
            self.game_sink.on_private_thought(agent, private_thought)

        self.game_sink.delay(delay)

    def _should_animate(self, speaker):
        is_system_speaker = isinstance(speaker, str) and speaker.upper() in self.RESERVED_NAMES
        is_human_speaker = hasattr(speaker, 'is_human') and speaker.is_human()
        return not (is_system_speaker or is_human_speaker)
    
    def _was_last_message_from_host(self):
        message_block = self.game_log._current_round_most_recent_conversation_entry()
        return message_block is not None and self.game_log._is_host_message(message_block, self.HOST_NAME)

    def _is_human(self, speaker):
        return hasattr(speaker, 'is_human') and speaker.is_human()
        
    def _should_hold(self, speaker):
        is_system_speaker = isinstance(speaker, str) and speaker.upper() in (self.RESERVED_NAMES - {self.HOST_NAME})
        is_repeated_host_message = isinstance(speaker, str) and speaker.upper() == self.HOST_NAME and self._was_last_message_from_host()
        return not (is_system_speaker or self._is_human(speaker) or is_repeated_host_message)

    def broadcast_public_action_agent(self, agent, message, private_thought_brief=None, color: str = "", directed_to_name = None,
                            is_reply = False, delay=0, widget=None):
        message_id = self.game_log._update_history(agent.name, message, private_thought_brief=private_thought_brief)

        self.game_sink.on_public_action(agent.name, message, color=color, animate_as_player=True, should_hold=True,
                                        directed_to_name = directed_to_name, is_reply = is_reply, is_human=agent.is_human(),
                                        widget=widget)
        self.game_sink.delay(delay)
        self.first_message_sent = True
        return message_id

    def broadcast_public_action_non_player(self, speaker: str, message: str, color: str = "", directed_to_name = None, is_reply = False, 
                                should_animate_override = False, is_human=False, pop_wrap=False, widget=None):
        
        if speaker.upper() == self.SYSTEM:
            raise ValueError("SYSTEM cannot broadcast a public_action; use system_broadcast instead") 
        #so its just host? and sys_admin // or is sys admin always private?
        self.game_log._update_history(speaker, message)
        is_repeated_host = speaker.upper() == self.HOST_NAME and self._was_last_message_from_host()
        should_hold = should_animate_override or not is_repeated_host
        self.game_sink.on_public_action(speaker, message, color=color, animate_as_player=should_animate_override, should_hold=should_hold,
                    directed_to_name = directed_to_name, is_reply = is_reply, is_human=is_human, pop_wrap=pop_wrap,
                    widget=widget)
        
    def system_broadcast(self, message, private=False, border_bottom = False):
        if not private:
            self.game_log._update_history(self.SYSTEM, message)
            self.game_sink.system_public(message, border_bottom = border_bottom)
        else:
            self.game_sink.system_private(message, border_bottom = border_bottom)

    def log_boundary(self, boundary: str):
        self.game_log._update_history("", boundary)

    def _is_sys_host_message(self, message_block):
        if len(message_block.message_entries) == 1:
            msg = message_block.message_entries[0]
            return msg.speaker in self.RESERVED_NAMES
        return False
        
    def host_broadcast(self, message, delay: float = 0.0, is_reply: bool = False,
                       animate_as_player=False, widget=None):
        entry = self.game_log._current_round_most_recent_conversation_entry()
        self.broadcast_public_action_non_player(self.HOST_NAME, message, is_reply=is_reply, should_animate_override=animate_as_player,
                                               widget=widget)
        self.game_sink.delay(delay)

    def delay(self, delay: float = 0.0):
        self.game_sink.delay(delay)

    def environment_broadcast(self, message, sender_name = ""):
        self.broadcast_public_action_non_player("", message, pop_wrap=True)
        self.game_sink.delay(2)

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
    
    def _rename_agent(self, agent_name, new_name):
        existing = [n for n in self.agent_names() if n != agent_name]
        new_name = self._unique_name(new_name, existing)
        self.agent_scores[new_name] = self.agent_scores.pop(agent_name)
        self.game_sink.on_points_update(dict(self.agent_scores))
        return new_name

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
        self.score_changed_in_round = True
        new_score = max(0, self.agent_scores[agent_name] + points)
        self.agent_scores[agent_name] = new_score
        self.game_sink.on_points_update(dict(self.agent_scores))

    def score_string(self) -> str:
        sorted_scores = sorted(self.agent_scores.items(), key=lambda item: item[1], reverse=True)
        return ", ".join(f"{name}: {score}" for name, score in sorted_scores)


    def is_typing(self, agent_name):
        self.is_typing_array.append(agent_name)
        self.game_sink.update_is_typing(list(self.is_typing_array))

    def done_typing(self, agent_name):
        self.is_typing_array.remove(agent_name)
        self.game_sink.update_is_typing(list(self.is_typing_array))
        
        
    def add_summary_commentary(self, agent_name, commentary):
        self.game_sink.add_summary_commentary_for_phase(agent_name, commentary, self.phase_number)