import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Sequence

from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class VoteElectLeader(VoteMechanicsMixin):
    @classmethod
    def display_name(cls, cfg):
        return "Elect the Executioner"

    @classmethod
    def rules_description(cls, cfg):
        return "Each player votes to elect the executioner. The leader chosen will have to choose who is going home."

    def _vote_for_leader(self, agent, all_names):
        eligible = all_names #[n for n in all_names if n != agent.name]
        user_content = (
            f"Vote for who you want to be the Executioner — the player who will choose who goes home. "
            f"Who do you nominate from: {', '.join(eligible)}?"
        )
        name_field_prompt = "The exact name of the player you nominate as Executioner."
        additional_thought_nudge = "What does it mean to elect an executioner? What will happen to them? What power will they have? Who would your choice send home?"
        action_fields = self._choose_name_field(eligible, name_field_prompt)
        response_model = DynamicModelFactory.create_model_(agent, model_name="vote_for_leader", action_fields=action_fields, additional_thought_nudge = additional_thought_nudge)
        return agent.take_turn_standard(user_content, self.gameBoard, response_model)

    def _collect_leader_votes(self, all_names: Sequence[str]):
        voting_futures = []
        with ThreadPoolExecutor() as executor:
            for agent in self.simulationEngine.agents:
                future = executor.submit(self._vote_for_leader, agent, all_names)
                voting_futures.append(future)
            voting_results = [f.result() for f in voting_futures]

        votes = []
        for agent, vote_response in zip(self.simulationEngine.agents, voting_results):
            #I think all public private responses with action should probably take an action as well, to output it
            self.publicPrivateResponse(agent, vote_response, delay = 1)
            target_name = getattr(vote_response, GamePromptLibrary.model_field_choose_name)
            choice = self._agent_by_name(target_name)
            if choice:
                votes.append(choice.name)
        return votes

    def run_vote(self, immunity_players: Optional[Sequence[str]]):
        immunity_players = self._validate_immunity(immunity_players)
        all_names = [a.name for a in self.simulationEngine.agents]
        players_up_for_elimination = [a.name for a in self._players_up_for_elimination(immunity_players)]

        # --- Step 1: Each player votes for a leader (anyone except themselves) ---
        host_message = "TIME TO ELECT THE EXECUTIONER. Each player will vote for who they want to carry the power to send someone home."
        self.gameBoard.host_broadcast(host_message)

        # Collect votes — everyone is eligible to be elected leader (including immune players)
        votes = self._collect_leader_votes(all_names)

        # --- Step 2: Tally — pick leader, random on tie ---
        vote_counts = Counter(votes)
        max_votes = max(vote_counts.values()) if vote_counts else 0
        top = [name for name, count in vote_counts.items() if count == max_votes]
        leader_name = random.choice(top)

        # --- Step 3: Leader reacts ---
        leader = next(a for a in self.simulationEngine.agents if a.name == leader_name)
        self.gameBoard.host_broadcast(
            f"The votes are in... {leader_name}, you have been elected Executioner. "
            f"With great power comes great vengeance. Who will you be sending home today, and why?"
        )
        host_message += self.immunity_string(immunity_players, players_up_for_elimination)

        # Leader chooses from non-immune players only
        action_fields = self._choose_name_field(players_up_for_elimination, "Choose who to send home.")
        response_model = DynamicModelFactory.create_model_(leader, model_name="elect_leader_choice", action_fields=action_fields)
        leader_response = leader.take_turn_standard(
            f"You have been elected Executioner. Choose who to eliminate from: {', '.join(players_up_for_elimination)}",
            self.gameBoard, response_model
        )
        self.publicPrivateResponse(leader, leader_response)

        # --- Step 4: Reveal and eliminate ---
        victim_name = getattr(leader_response, GamePromptLibrary.model_field_choose_name)
        if not victim_name or victim_name not in players_up_for_elimination:
            self.gameBoard.host_broadcast(f"⚡ {leader_name} has made an invalid choice of... {victim_name}.")
            victim_name = random.choice(players_up_for_elimination)
            self.gameBoard.host_broadcast(f"⚡Instead, {victim_name} will be sent home.")
        else:
            self.gameBoard.host_broadcast(f"⚡ {leader_name} has made their choice... {victim_name} will be going home.")
        #perfect opportunity to run thru the model to make a joke or pun
        self.eliminate_player_by_name(victim_name)
        self.gameBoard.host_broadcast(f"⚡ {leader_name}, thank you for your service. Your time as executioner has come to an end... unless a re-election?")
        