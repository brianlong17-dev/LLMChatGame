from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import random
from typing import Callable, Literal, Sequence
from pydantic import Field
from agents.base_agent import BaseAgent
from models.player_models import DynamicModelFactory
from prompts.prompts import PromptLibrary
from prompts.gamePrompts import GamePromptLibrary
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
        self._buffer_amount = 0.6 #default
        self._debug = True

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
        if not field_description:
            field_description = "Your final choice."
        choice_definition = (Literal[*choices], Field(description=field_description))
        return {field_name: choice_definition}

    def create_basic_field(self, field_name, field_description):
        field_definition = (str, Field(description=field_description))
        return {field_name: field_definition}

    def _choose_name_field(self, allowed_names, reason_for_choosing_prompt, field_name = None):
        if not field_name:
            field_name = GamePromptLibrary.model_field_choose_name
        choice_reason_prompt = f"The exact name of the agent. {reason_for_choosing_prompt}"
        return self.create_choice_field(field_name, allowed_names, choice_reason_prompt)

    #####################
    #   Player Turns    #
    #####################

    def respond_to(self, player: Debater, text_to_respond_to: str, public_response_prompt: str = None,
                   private_thoughts_prompt: str = None, instruction_override = None):
        model = DynamicModelFactory.create_model_(player, public_response_prompt=public_response_prompt,
                                                     private_thoughts_prompt=private_thoughts_prompt)
        return player.take_turn_standard(text_to_respond_to, self.gameBoard, model, instruction_override=instruction_override)

    def _make_player_turn(self, player: Debater, user_prompt: str, response_model):
        return player.take_turn_standard(user_prompt, self.gameBoard, response_model)

    def get_response(self, player, model_name, context_msg, action_fields = None, additional_thought_nudge = None):
        model = DynamicModelFactory.create_model_(
            player,
            model_name,
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields
        )
        return player.take_turn_standard(context_msg, self.gameBoard, model)

    def _ask_directed_question(self, player, possible_target_names, user_content,
                               public_response_prompt, additional_thought_nudge = None):
        action_fields = self._choose_name_field(possible_target_names, "Who your question/statement is directed to. ")
        model = DynamicModelFactory.create_model_(player, action_fields=action_fields,
            public_response_prompt=public_response_prompt, additional_thought_nudge=additional_thought_nudge)
        result = player.take_turn_standard(user_content, self.gameBoard, model)
        self.gameBoard.handle_public_private_output(player, result)
        return result

    def _basic_turn(self, agent, user_content_prompt, public_response_prompt, private_thoughts_prompt = None, optional = False):
        response_model = DynamicModelFactory.create_model_(agent, "basic_turn", public_response_prompt=public_response_prompt,
                        private_thoughts_prompt=private_thoughts_prompt, optional=optional)
        if optional:
            result = self._basic_turn_optional(response_model, agent, user_content_prompt)
        else:
            result = agent.take_turn_standard(user_content_prompt, self.gameBoard, response_model)

        if result and result.public_response:
            self.gameBoard.handle_public_private_output(agent, result)

    def _basic_turn_optional(self, model, agent, user_content_prompt):
        agent.optional_response_buffer = round(agent.optional_response_buffer + self._buffer_amount, 2)
        if agent.optional_response_buffer < 1:
            self._low_buffer_message(agent)
            return None
        else:
            optional_response_prompt = (f"Optional response. In each optional response, your buffer increases by {self._buffer_amount}. "
                f"Your current buffer: {agent.optional_response_buffer} - responding spends 1 unit from the buffer. ")
            user_content_prompt += f"\n{optional_response_prompt}\n"
            result = agent.take_turn_standard(user_content_prompt, self.gameBoard, model)
            if result.public_response:
                agent.optional_response_buffer = round(agent.optional_response_buffer - 1, 2)
                self.debug_print(f"{agent.name} spending buffer ")
            else:
                self.debug_print(f"{agent.name} passes, buffer: {agent.optional_response_buffer}")
                self.debug_print(f"{agent.name} thoughts: {result.private_thoughts}")
            return result

    def _low_buffer_message(self, agent):
        self.private_system_message(agent, "Your turn here was passed as your optional response buffer was too low.")

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
        return result.public_response

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
