from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import random
from typing import Callable, Sequence
from agents.base_agent import BaseAgent
from models.player_models import DynamicModelFactory
from gameplay_management.turn_manager import TurnManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agents.player import Debater


class BaseRound:

    #####################
    #   Setup / Meta    #
    #####################

    def __init__(self, gameBoard, simulationEngine):
        self.gameBoard = gameBoard
        self.simulationEngine = simulationEngine
        self._debug = True
        self.turn_manager = TurnManager(self)

    def publicPrivateResponse(self, agent: BaseAgent, result, delay: float = 0.0, action_string = ""):
        #TODO deprecate
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

    #####################
    #   Agent Access    #
    #####################

    def agents(self):
        return self.simulationEngine.agents

    def dead_agents(self):
        return self.simulationEngine.dead_agents

    def cfg(self):
        return self.simulationEngine.gameplay_config

    def _names(self, agents: Sequence["Debater"]) -> list[str]:
        return [agent.name for agent in agents]

    def _agent_by_name(self, name, incl_dead = False):
        agents = list(self.simulationEngine.agents)
        if incl_dead:
            agents += self.simulationEngine.dead_agents
        return next((agent for agent in agents if agent.name == name), None)

    def _shuffled_agents(self):
        agents = list(self.simulationEngine.agents)
        return random.sample(agents, k=len(agents))

    def get_strategic_players(self, available_agents, top_player = True, multiple = False) -> list[Debater]:
        """
        Selects a player from available_agents based on rank.
        mode="top": Picks from the leaders.
        mode="bottom": Picks from the tail-enders.
        """
        agent_names = self._names(available_agents)
        current_scores = {name: score for name, score in self.gameBoard.agent_scores.items()
                        if name in agent_names}
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

    #####################
    #   Broadcasting    #
    #####################

    def _host_broadcast(self, message, delay = 0):
        self.gameBoard.host_broadcast(message, delay)

    def _host_broadcast_multiple_choice(self, messages):
        self.gameBoard.host_broadcast(random.choice(messages))

    def _host_current_round_history(self):
        return self.gameBoard.context_builder.current_round_formatted(self.simulationEngine.game_master)

    def private_system_message(self, agent, message, silent = False):
        admin = self.gameBoard.SYS_ADMIN
        restricted_users = [admin, agent.name]
        id = self.gameBoard.log_new_restricted_conversation(restricted_users, admin, message)
        self.gameBoard.close_private_conversation(id, silent)

    ###########################
    #   Model Field Builders  #
    ###########################

    def create_choice_field(self, field_name, choices, field_description = None):
        return self.turn_manager.create_choice_field(field_name, choices, field_description)

    def create_basic_field(self, field_name, field_description):
        return self.turn_manager.create_basic_field(field_name, field_description)

    def _choose_name_field(self, allowed_names, reason_for_choosing_prompt, field_name = None):
        return self.turn_manager._choose_name_field(allowed_names, reason_for_choosing_prompt, field_name)

    #####################
    #   Player Turns    #
    #####################

    def respond_to(self, player: Debater, text_to_respond_to: str, public_response_prompt: str = None,
                   private_thoughts_prompt: str = None, instruction_override = None):
        return self.turn_manager.respond_to(player, text_to_respond_to, public_response_prompt, private_thoughts_prompt, instruction_override)

    def get_response(self, player, model_name, context_msg, action_fields = None, additional_thought_nudge = None):
        return self.turn_manager.get_response(player, model_name, context_msg, action_fields, additional_thought_nudge)

    def _ask_directed_question(self, player, possible_target_names, user_content,
                               public_response_prompt, additional_thought_nudge = None):
        return self.turn_manager._ask_directed_question(player, possible_target_names, user_content, public_response_prompt, additional_thought_nudge)

    def _basic_turn(self, agent, user_content_prompt, public_response_prompt, private_thoughts_prompt = None, optional = False):
        return self.turn_manager._basic_turn(agent, user_content_prompt, public_response_prompt, private_thoughts_prompt, optional)

    ###########################
    #   Parallel Execution    #
    ###########################

    def _run_tasks(
        self,
        tasks: list[tuple], #list of arguments
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

    ###########################
    #   Private Conversation  #
    ###########################

    def _initialise_private_host_conversation(self, player, message):
        users = ["Host", player.name]
        conversation_id = self.gameBoard.log_new_restricted_conversation(users, "Host", message)
        return conversation_id

    def _private_host_conversation_host_message(self, conversation_id, message):
        self.gameBoard.log_message_to_conversation(conversation_id, "Host", message)

    def _private_host_conversation_get_response(self, player, conversation_id, public_response_prompt, instruction_override = None):
        basic_model = DynamicModelFactory.create_model_(player, "basic_turn", public_response_prompt=public_response_prompt)
        user_content = "Respond privately to the host. "
        result = player.take_turn_standard(user_content, self.gameBoard, basic_model, instruction_override=instruction_override)
        self.gameBoard.log_message_to_conversation(conversation_id, player.name, result.public_response)
        return result

    #####################
    #   Utilities       #
    #####################

    def points_string(self, count):
        return "a point" if count == 1 else f"{count} points"

    def format_list(self, lst):
        if not lst:
            return ""
        if len(lst) == 1:
            return str(lst[0])
        return ", ".join(map(str, lst[:-1])) + " and " + str(lst[-1])

    def debug_print(self, string):
        if self._debug:
            print(string)
