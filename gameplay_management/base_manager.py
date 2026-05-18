from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import random
from typing import Callable, Sequence
from agents.base_agent import BaseAgent
from models.player_models import DynamicModelFactory
from gameplay_management.turn_manager import TurnManager
from pydantic import Field

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

    @property
    def game_log(self):
        return self.gameBoard.game_log

    def publicPrivateResponse(self, agent: BaseAgent, result, delay: float = 0.0, is_reply = False):
        #TODO deprecate
        self.gameBoard.handle_public_private_output(agent, result, delay, is_reply=is_reply)

    @classmethod
    def is_discussion(cls):
        return False

    @classmethod
    def is_game(cls):
        return False

    @classmethod
    def is_vote(cls):
        return False
    
    @classmethod
    def rules_brief(cls, cfg):
        return ""

    #####################
    #   Agent Access    #
    #####################

    @property
    def agents(self):
        return self.simulationEngine.agents

    @property
    def human_player(self):
        return next((agent for agent in self.agents if agent.is_human()), None)
       
    def _other_agents(self, agent, agents):
        return [a for a in agents if a != agent]
    
    def dead_agents(self):
        return self.simulationEngine.dead_agents

    @property
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

    def _host_broadcast(self, message, delay = 0, is_reply = False):
        self.gameBoard.host_broadcast(message, delay, is_reply=is_reply)

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
    
    def _host_back_and_forth(self, player, questions, instruction_override=None, conversation_id = None):
    
        action_fields = {}
        for key, value in questions.items():
            action_fields = action_fields | {key: (str, Field(description=value))}

        basic_model = DynamicModelFactory.create_model_(
            player, "basic_turn",
            action_fields=action_fields,
            action_post_response=True #need - we're overwriting public response
        )
        user_content = "Respond privately to each question, back and forth with the host."
        result = player.take_turn_standard(
            user_content, self.gameBoard, basic_model,
            instruction_override=instruction_override
        )
        for key, value in questions.items():
            answer = getattr(result, key, "")
            if not conversation_id:
                conversation_id = self._initialise_private_host_conversation(player, value)
            else:
                self._private_host_conversation_host_message(conversation_id, value)
            self.gameBoard.log_message_to_conversation(conversation_id, player.name, answer)
        return conversation_id


    #####################
    #   Utilities       #
    #####################

    def points_string(self, count):
        return "1 point" if count == 1 else f"{count} points"

    def format_list(self, lst):
        if not lst:
            return ""
        if len(lst) == 1:
            return str(lst[0])
        return ", ".join(map(str, lst[:-1])) + " and " + str(lst[-1])

    def debug_print(self, string):
        if self._debug:
            print(string)

    #####################
    #   Widgets         #
    #####################
    
    
                    
    def _initialise_voting_widget(self, nominee_names, voter_names, theme="gold"):
        self._voting_dictionary = {
            "kind": "voting",
            "theme": theme,
            "nominees": [{"name": name, "votes": 0} for name in nominee_names],
            "voters_done": [],
            "voters_pending": list(voter_names),
            "is_final": False,
        }
        self.gameBoard.game_sink.on_widget_update(self._voting_dictionary)
                
    
    def _update_voting_widget(self, voter_name, target_name, is_final=False):
        for nominee in self._voting_dictionary["nominees"]:
            if nominee["name"] == target_name:
                nominee["votes"] += 1
                break
        self._voting_dictionary["voters_pending"] = [
            n for n in self._voting_dictionary["voters_pending"] if n != voter_name
        ]
        
        # ---- (edge case - tie breaker second vote) ---- #
        voters_done = self._voting_dictionary["voters_done"]
        existing = next((v for v in voters_done if v["name"] == voter_name), None)
        if existing:
            existing["voted_for"] = target_name
        else:
            voters_done.append({"name": voter_name, "voted_for": target_name})
        # ------------------------------------------------ #
        self._voting_dictionary["is_final"] = is_final
        self.gameBoard.game_sink.on_widget_update(self._voting_dictionary)
        
    def _vote_widget_vote_finalised(self):
        self._voting_dictionary["is_final"] = True
        self.gameBoard.game_sink.on_widget_update(self._voting_dictionary)
        