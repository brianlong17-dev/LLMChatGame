from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
import random

class GamePrisonersDilemma(GameMechanicsMixin):

    @classmethod
    def display_name(cls, cfg):
        return "Prisoner's Dilemma"

    @classmethod
    def rules_description(cls, cfg):
        return f"Players will choose to split or steal to win points. {cls.pairing_method_string(cfg)}"

    @classmethod
    def pairing_method_string(cls, cfg):
        pairing_method = cfg.pd_pairing_method
        if pairing_method == cfg.pd_pairing_choice_random:
            return "In a random order, players get to choose their partner."
        elif pairing_method == cfg.pd_pairing_choice_lowest:
            return "In order of lowest score, players get to choose their partner."
        elif pairing_method == cfg.pd_pairing_choice_all:
            return "Every player will face every other player once."
        return "Players will be paired randomly."

    def points_rules_string(self):
        cfg = self.cfg()
        pd_split=cfg.pd_points_split
        pd_steal=cfg.pd_points_steal
        pd_both_steal=cfg.pd_points_both_steal
        points_str = (
            f"- If you both SPLIT, you both get {pd_split} points.\n"
            f"- If you STEAL and they SPLIT, you get {pd_steal} points and they get 0.\n"
            f"- If you both STEAL, you both get {pd_both_steal} point.\n")
        return points_str

    def get_split_or_steal(self, player, opponent):
        user_content = GamePromptLibrary.pd_game_prompt.format(opponent_name=opponent.name,
                                                               points_rules_string=self.points_rules_string())
        choices = ["split", "steal"]
        action_fields = self.create_choice_field("action", choices)
        additional_thought_nudge="What points are available? How will the next elimination work? Do you need points or alliance?"
        model = DynamicModelFactory.create_model_(player, "split_or_steal",
                    additional_thought_nudge=additional_thought_nudge, action_fields=action_fields)
        return player.take_turn_standard(user_content, self.gameBoard, model)

    def _calculate_pd_payout(self, choice0, choice1, name0, name1):
        cfg = self.cfg()
        splitPoints=cfg.pd_points_split
        stealPoints=cfg.pd_points_steal
        bothSteal=cfg.pd_points_both_steal
        choice0 = choice0.strip().lower().replace(".", "")
        choice1 = choice1.strip().lower().replace(".", "")

        outcomes = {
            ('split', 'split'): (splitPoints, splitPoints, f"Congratulations {name0} and {name1}. You both SPLIT! "),
            ('steal', 'steal'): (bothSteal, bothSteal, f"OH NO {name0} and {name1}... You both STOLE. "),
            ('steal', 'split'): (stealPoints, 0, f"OH NO! {name0} STOLE from {name1}! "),
            ('split', 'steal'): (0, stealPoints, f"OH NO! {name1} STOLE from {name0}! ")
        }

        p0_gain, p1_gain, msg = outcomes.get(
            (choice0, choice1),
            (0, 0, f"Someone hallucinated a move! No points awarded."))
        return p0_gain, p1_gain, msg

    def _get_pairs(self):
        cfg = self.cfg()
        agents = list(self.simulationEngine.agents)
        random.shuffle(agents)

        if cfg.pd_pairing_method == cfg.pd_pairing_choice_all:
            return list(combinations(agents, 2)), None

        choose_partner = cfg.pd_pairing_method in (cfg.pd_pairing_choice_random, cfg.pd_pairing_choice_lowest)
        loser_picks_first = cfg.pd_pairing_method == cfg.pd_pairing_choice_lowest
        return self._generate_pairings(agents, choose_partner, loser_picks_first)

    def _execute_pairs(self, pairs):
        for agent0, agent1 in pairs:
            self.gameBoard.host_broadcast(f"{agent0.name} vs {agent1.name}. Split or Steal?\n")

            with ThreadPoolExecutor() as executor:
                future0 = executor.submit(self.get_split_or_steal, agent0, agent1)
                future1 = executor.submit(self.get_split_or_steal, agent1, agent0)
                results = [future0.result(), future1.result()]

            choices = []
            for agent, res in zip((agent0, agent1), results):
                self.publicPrivateResponse(agent, res)
                choices.append(res.action.strip().lower())

            p0_gain, p1_gain, msg = self._calculate_pd_payout(choices[0], choices[1], agent0.name, agent1.name)

            for agent, gain in zip((agent0, agent1), (p0_gain, p1_gain)):
                self.gameBoard.append_agent_points(agent.name, gain)

            result_host_message = f"{msg}{agent0.name} receives {p0_gain}, and {agent1.name} receives {p1_gain} points."
            self.gameBoard.host_broadcast(f"{result_host_message}\n")

            for agent in (agent0, agent1):
                reaction = self.respond_to(agent, result_host_message)
                self.publicPrivateResponse(agent, reaction)

    def run_game(self):
        intro_message = GamePromptLibrary.prisonersDilemmaIntro(self.pairing_method_string(self.cfg()),
            self.points_rules_string())
        self.gameBoard.host_broadcast(intro_message)

        pairs, leftover = self._get_pairs()

        if leftover:
            auto_points = self.cfg().pd_odd_player_auto_points
            self.gameBoard.host_broadcast(f"{leftover.name} is the odd one out this round! They automatically receive {auto_points} points.\n\n")
            self.gameBoard.append_agent_points(leftover.name, auto_points)

        self._execute_pairs(pairs)
