from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import random
from typing import Callable, Sequence
from agents.base_agent import BaseAgent
from gameplay_management.human_turn_form import HumanInputDescription
from gameplay_management.turn_manager import TurnManager
from pydantic import Field

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agents.abstract_agentic_player import AbstractAgenticPlayer


class BaseRound:

    TARGET_NAME_FIELD = "target_name"

    #####################
    #   Setup / Meta    #
    #####################

    def __init__(self, game_board, simulationEngine):
        self.game_board = game_board
        self.simulationEngine = simulationEngine
        self._debug = True
        self.turn_manager = TurnManager(self)

    @property
    def game_log(self):
        return self.game_board.game_log
    
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
    def is_finale(cls):
        return False

    @classmethod
    def round_type(cls):
        if cls.is_finale():
            return "finale"
        if cls.is_vote():
            return "elimination"
        if cls.is_game():
            return "game"
        if cls.is_discussion():
            return "discussion"
        return None

    @classmethod
    def rules_brief(cls, cfg):
        return ""

    #####################
    #   Function        #
    #####################
    
    def _human_result_description(self, title, placeholder):
        return HumanInputDescription(
            titles={"public_response": title},
            placeholders={"public_response": placeholder},
        )

    def _human_elimination_description(self):
        return HumanInputDescription(
            titles={"public_response": "You lose :(  Any final words?"},
            placeholders={"public_response": "your farewell message"},
            underlines=["last thing they'll ever hear from you"],
        )

    def eliminate_player_by_name(self, player_name, elimination_context=None):
        victim = self._agent_by_name(player_name) 
        elimination_context = ': ' + elimination_context if elimination_context else ". "
            
        victim.game_over = True
        self.game_board.host_broadcast(self.cfg.pre_eviction_message.format(victim_name=victim.name.upper()))
        self.simulationEngine.eliminate_player(victim)
        turn_prompt = (
            f"---------------------------------------------------------------------\n"
            f"!!!GAME OVER!!!\n"
            f"You're being removed! React to what just happened{elimination_context}\n"
            f"(NOTE: Drop any pretense hiding your true intentions.)\n"
            f"---------------------------------------------------------------------\n"
            f"Your response:")
        
        final_words_prompt = ("Mask drop moment- let your inner voice speak. Speak directly to specific players.")
        if False: #host_question:
            final_words_prompt += f"Respond to the host's question: {host_question}"
        
        final_words_response= self.turn_manager.take_turn(victim, turn_prompt, public_response_prompt=final_words_prompt,
                                                           additional_thought_nudge="Are you mad at anyone? What have you been holding back? ", speech=True,
                                                           human_input_description_object=self._human_elimination_description())
        
        self.turn_manager._output_response(victim, final_words_response)
        
        self.game_board.system_broadcast(self.cfg.post_eviction_system_message.format(victim_name=victim.name), private = False)

    #####################
    #   Agent Access    #
    #####################
    
    def _name_choice_field(self):
        return "target_name"

    @property
    def agents(self):
        return self.simulationEngine.agents

    @property
    def human_player(self):
        return next((agent for agent in self.agents if agent.is_human()), None)
       
    def _other_agents(self, agent, agents = None):
        if agents is None:
            agents = self.agents
        return [a for a in agents if a != agent]
    
    def dead_agents(self):
        return self.simulationEngine.dead_agents
    
    @property
    def non_human_agents(self):
        return [agent for agent in self.agents if not agent.is_human()]

    @property
    def cfg(self):
        return self.simulationEngine.gameplay_config

    def _names(self, agents: Sequence["AbstractAgenticPlayer"]) -> list[str]:
        return [agent.name for agent in agents]
    
    def _opponent_names(self, player):
        return [agent.name for agent in self.agents if agent != player]

    def _agent_by_name(self, name, incl_dead = False):
        agents = list(self.simulationEngine.agents)
        if incl_dead:
            agents += self.simulationEngine.dead_agents
        return next((agent for agent in agents if agent.name == name), None)

    def _shuffled_agents(self):
        agents = list(self.simulationEngine.agents)
        return random.sample(agents, k=len(agents))
    
    def _agent_score(self, agent_name):
        return self.game_board.agent_scores[agent_name] 

    def get_strategic_players(self, available_agents, top_player = True, multiple = False) -> list[AbstractAgenticPlayer]:
        """
        Selects a player from available_agents based on rank.
        mode="top": Picks from the leaders.
        mode="bottom": Picks from the tail-enders.
        """
        agent_names = self._names(available_agents)
        current_scores = {name: score for name, score in self.game_board.agent_scores.items()
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

    def _host_broadcast(self, message, delay = 0, is_reply = False, animate_as_player=False, widget=None):
        self.game_board.host_broadcast(message, delay, is_reply=is_reply, animate_as_player=animate_as_player, widget=widget)

    def _host_broadcast_multiple_choice(self, messages):
        self.game_board.host_broadcast(random.choice(messages))

    def _host_current_round_history(self):
        return self.game_board.context_builder.current_round_formatted(self.simulationEngine.game_master)

    def private_system_message(self, agent, message, silent = False):
        admin = self.game_board.SYS_ADMIN
        restricted_users = [admin, agent.name]
        id = self.game_board.log_new_restricted_conversation(restricted_users, admin, message)
        self.game_board.close_private_conversation(id, silent)

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
        conversation_id = self.game_board.log_new_restricted_conversation(users, "Host", message)
        return conversation_id

    def _private_host_conversation_host_message(self, conversation_id, message):
        self.game_board.log_message_to_conversation(conversation_id, "Host", message)

    def _private_host_conversation_get_response(self, player, conversation_id, public_response_prompt, instruction_override = None):
        result = self.turn_manager.take_turn(player, "Respond privately to the host. ",
            model_name="basic_turn",
            public_response_prompt=public_response_prompt,
            instruction_override=instruction_override)
        self.game_board.log_message_to_conversation(conversation_id, player, result.public_response)
        return result
    
    def _host_back_and_forth(self, player, questions, instruction_override=None, conversation_id = None):
    
        action_fields = {}
        for key, value in questions.items():
            action_fields = action_fields | {key: (str, Field(description=value))}

        result = self.turn_manager.take_turn(
            player, "Respond privately to each question, back and forth with the host.",
            model_name="basic_turn",
            action_fields=action_fields,
            action_post_response=True,
            instruction_override=instruction_override,
            multi_answer_model=True
        )
        for key, value in questions.items():
            answer = getattr(result, key, "")
            if not conversation_id:
                conversation_id = self._initialise_private_host_conversation(player, value)
            else:
                self._private_host_conversation_host_message(conversation_id, value)
            self.game_board.log_message_to_conversation(conversation_id, player, answer)
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
    
    def _copy_without(self, a_list, an_item):
        return [o for o in a_list if o != an_item]
    
    def _push_voting_widget_winners(self, winner_names):
        self._voting_dictionary["winners"] = list(winner_names)
        self._voting_dictionary["is_final"] = True
        self.game_board.game_sink.on_widget_update(self._voting_dictionary)

    
    def _push_voting_widget_losers(self, loser_names):
        self._voting_dictionary["losers"] = list(loser_names)
        self._voting_dictionary["is_final"] = True
        self.game_board.game_sink.on_widget_update(self._voting_dictionary)
                    
    def _initialise_voting_widget(self, nominee_names, voter_names, theme="gold"):
        self._voting_dictionary = {
            "kind": "voting",
            "theme": theme,
            "nominees": [{"name": name, "votes": 0} for name in nominee_names],
            "voters_done": [],
            "voters_pending": list(voter_names),
            "is_final": False,
        }
        self.game_board.game_sink.on_widget_update(self._voting_dictionary)
                
    
    def _build_voting_widget_update(self, voter_name, target_name, is_final=False):
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
        return self._voting_dictionary
        
    def _vote_widget_vote_finalised(self):
        self._voting_dictionary["is_final"] = True
        self.game_board.game_sink.on_widget_update(self._voting_dictionary)
        