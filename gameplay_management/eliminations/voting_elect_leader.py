import random
from collections import Counter

from gameplay_management.eliminations.voting_round_base import VotingRoundBase
from gameplay_management.human_turn_form import HumanInputDescription


class VoteElectLeader(VotingRoundBase):
    @classmethod
    def display_name(cls, cfg):
        return "Elect the Executioner"

    @classmethod
    def rules_description(cls, cfg):
        return "Each player votes to elect the executioner. The leader chosen will have to choose who is going home."

    @classmethod
    def rules_brief(cls, cfg):
        return "Vote to elect a leader- the leader chooses who to send home."
    
    
    def _game_intro(self):
        intro = (
            "TIME TO *ELECT THE EXECUTIONER*. The elected player will have the power, and the burden "
            "to send one player home. "
            "You will receive one point per vote received. "
        )
        if self.immunity_plus:
            intro += ("Each player who receives a nomination will be immune and safe from elimination. ")
        return intro


    def _human_elect_description(self):
        return HumanInputDescription(
            titles={
                self.TARGET_NAME_FIELD: "Who do you elect as Executioner?",
                "public_response": "(Optional) Why?",
            },
            placeholders={"public_response": "explain, or pitch yourself"},
            underlines=["your vote also keeps them safe"] if self.immunity_plus else [],
        )

    def _human_plea_description(self):
        return HumanInputDescription(
            titles={"public_response": "You're at risk. Make your plea."},
            placeholders={"public_response": "why should they spare you?"},
        )

    def _human_execution_description(self):
        return HumanInputDescription(
            titles={
                self.TARGET_NAME_FIELD: "Who are you sending home?",
                "public_response": "What do you say?",
            },
            placeholders={"public_response": "explain your heavy burden"},
            underlines=["your choice is revealed after your explanation"],
        )

    def _human_clean_hands_description(self):
        return HumanInputDescription(
            titles={"public_response": "You never had to choose. What do you say?"},
            placeholders={"public_response": "relieved? disappointed?"},
        )

    def run_vote(self):
        self.immunity_plus = True
        # 1. intro
        intro = self._game_intro()
        self.game_board.host_broadcast(intro)

        all_names = [a.name for a in self.simulationEngine.agents]
        self._initialise_voting_widget(all_names, all_names, theme="gold")

        # 2. vote
        votes = []
        for player in self.simulationEngine.agents:
            possible_vote_targets = all_names if not self.immunity_plus else self._copy_without(all_names, player.name)
            turn_prompt = (
                "Cast your vote for the executioner- who gets to send one player home. "
                f"Choose from: {', '.join(possible_vote_targets)}."
            )
            if self.immunity_plus:
                turn_prompt += "Remember: voting for someone also keeps them *safe* from elimination. (You cannot vote for yourself). "
            public_response_prompt = (
                "What do you say after you reveal your choice? "
                "Optional - you can also make your own pitch to be nominated. "

            )
            additional_thought_prompt = (
                "Who would be the best nominee as executioner from your specific perspective? "
                
            )
            if self.immunity_plus:
                additional_thought_prompt += "Do you need to nominate someone to give them immunity? Are you at risk- Do you want to ask for a nomination from who hasn't voted yet? "
            action_fields = self.turn_manager._choose_name_field(possible_vote_targets, "The player you elect as Executioner.")
            vote_response = self.turn_manager.take_turn(
                player, turn_prompt,
                model_name="vote_for_leader",
                public_response_prompt=public_response_prompt,
                additional_thought_nudge=additional_thought_prompt,
                action_fields=action_fields,
                human_input_description_object=self._human_elect_description(),
            )

            choice = self.turn_manager._get_target_name_from_response(vote_response)
            self.turn_manager._output_response(
                player, vote_response, is_reply=True,
                pre_message_choice_reveal=self.TARGET_NAME_FIELD,
                widget=self._build_voting_widget_update(player.name, choice or "—"),
            )
            if choice:
                votes.append(choice)
                
        self._process_votes(votes)
        

    def _process_votes(self, votes):
        vote_counts = Counter(votes)
        nominees = [nominee for nominee in vote_counts]
        host_msg = f"Congrats our nominees {self.format_list(nominees)}. You will each receive one point per vote received. "
        eligible = [agent.name for agent in self.agents if agent.name not in nominees]


        for nominee, count in vote_counts.items():
            self.game_board.append_agent_points(nominee, count)
       
        max_votes = max(vote_counts.values())
        top_scorers = [name for name, count in vote_counts.items() if count == max_votes]
        if len(top_scorers) > 1:
            tied_agents = [self._agent_by_name(name) for name in top_scorers]
            score_leaders = self.get_strategic_players(tied_agents, top_player=True, multiple=True)
            if len(score_leaders) == 1:
                winner_name = score_leaders[0].name
                host_msg += f"With a tie for most votes, our scoreboard leader will be chosen as executioner: \n*{winner_name}*. "
            else:
                winner_name = random.choice(score_leaders).name
                host_msg += f"With a tie for votes and on points, a random executioner will be...\n{winner_name}! "
        else:
            winner_name = top_scorers[0]
            host_msg += f"With {max_votes} votes our chosen executioner is: \n*{winner_name}*"
            
        self._push_voting_widget_winners([winner_name])
        self._host_broadcast(host_msg)
        
            
        if self.immunity_plus:
            if len(eligible) == 1:
                self._one_nominee(winner_name, eligible[0])
                return
            elif len(eligible) == 0:
                nominee_message = "As every player received one vote, each player is again vulnerable. "
                eligible = [agent.name for agent in self.agents if agent.name != winner_name]
            else:
                nominee_message = f"The following players did not receive a vote, and will now be up for elimination: \n*{self.format_list(eligible)}.*"
            self._host_broadcast(nominee_message)
        else:
            eligible = [agent.name for agent in self.agents if agent.name != winner_name]




        self._make_execution_decision(winner_name, eligible )
    

    def _one_nominee(self, winner_name, loser_name):
        host_question = (f"Sadly- only one player did not receive a nomination. It hardly seems fair, but we now say goodbye to our beloved \n{loser_name}. ")
        self._host_broadcast(host_question)
        self._push_voting_widget_losers([loser_name])
        elimination_context_string = "You were the only player not to receive a vote which provides immunity, so you are being sent home by default. "
        self.eliminate_player_by_name(loser_name, elimination_context_string)
        host_question = (f"And to our executioner {winner_name}- Your time is up as executioner and you never had to make a decision, so your hands are clean. "
                             "Are you happy you didn't have to choose, or did you want to get your hands dirty?"
                             "If you could have given someone the axe, who would it have been? ")
        self._host_broadcast(host_question)
        self.turn_manager.respond_to(self._agent_by_name(winner_name), turn_prompt=f"Respond to the events of the round: {loser_name}'s last words, and to the hosts question: {host_question}",
                                     private_thoughts_prompt="What do you want to reveal? ", prefix_turn_prompt=False, broadcast=True,
                                     human_input_description_object=self._human_clean_hands_description())
        
        #go to winner for reaction 

    def _make_execution_decision(self, nominee, eligible):
        leader = self._agent_by_name(nominee)

        if len(eligible) < 6:
            self.game_board.host_broadcast(
                f"Before {nominee} decides, those at risk get one last word. Make your plea."
            )
            for name in eligible:
                pleader = self._agent_by_name(name)
                self.turn_manager.respond_to(
                    pleader,
                    turn_prompt=f"You are at risk of being sent home by {nominee}. Make your final plea — why should they spare you?",
                    private_thoughts_prompt="What is your read on the executioner? What angle will actually move them?",
                    prefix_turn_prompt=False,
                    broadcast=True,
                    is_reply=True,
                    human_input_description_object=self._human_plea_description()
                )

        self.game_board.host_broadcast(
            f"{nominee} Who will you be sending home today?"
        )
        
        

        additional_thought_prompt = (
            "You hold the power to send someone home. "
            "How are you feeling about this? "
            "There are several players you could choose. "
            "Reason through your character — what are you feeling as a person? Is your heart heavy, "
            "or is it just logical? Who do you choose?"
        )
        public_response_prompt = (
            "What do you say as Executioner? How are you feeling? "
            "Your choice will be revealed afterwards, so weigh your words. "
        )
        action_fields = self.turn_manager._choose_name_field(eligible, "the player you send home.")

        leader_response = self.turn_manager.take_turn(
            leader,
            f"You have been elected Executioner. Choose who to eliminate from: {', '.join(eligible)}",
            model_name="elect_leader_choice",
            public_response_prompt=public_response_prompt,
            additional_thought_nudge=additional_thought_prompt,
            action_fields=action_fields,
            is_reply=True,
            human_input_description_object=self._human_execution_description()
        )

        # broadcast choice — post reveal
        self.turn_manager._output_response(leader, leader_response, post_message_choice_reveal=self.TARGET_NAME_FIELD)

        # manage execution
        victim_name = self.turn_manager._get_target_name_from_response(leader_response)
        host_question = f"How does it feel to be sent home by {leader.name}? "
        self.game_board.host_broadcast(f"⚡ {nominee} has made their choice... {victim_name} will be going home. {host_question}")
        self._push_voting_widget_losers([victim_name])
        
        elimination_context = f"You were up for elimination with {self.format_list(self._copy_without(eligible, victim_name))}. {nominee} chose to send you home."
        self.eliminate_player_by_name(victim_name, elimination_context=elimination_context)
        
        if len(eligible) == 2:
            safe_player_names = self._copy_without(eligible, victim_name)
            for safe_player_name in safe_player_names:
                host_msg = (f"Wow- {safe_player_name} - you narrowly survived this one- how are you feeling? What lessons will you take forward?")
                self._host_broadcast(host_msg)
                self.turn_manager.respond_to(self._agent_by_name(safe_player_name), "Your turn: respond to the events above, and to the hosts question.", private_thoughts_prompt = "How are you feeling, and how does that impact what you want to say? ", broadcast=True, is_reply=True,
                                             human_input_description_object=self._human_survivor_description())
