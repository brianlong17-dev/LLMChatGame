
import random
from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary

class FinaleReunionRound(VoteMechanicsMixin):

    @classmethod
    def display_name(cls, cfg):
        return "Finale Reunion Round"

    @classmethod
    def rules_description(cls, cfg):
        return "This is a reunion round"

    @classmethod
    def is_discussion(cls):
        return False

    @classmethod
    def is_private_round(cls):
        return False


    def _wake_up_player_reunion(self, player):
            #--------- First message ---------
            host_message = ("Hey, welcome back to the game. You have been watching since your elimination. "
            "But now you will have a chance to have your say- to air any grievances or settle any scores. "
            "At the end of this round you and the other eliminated players will get to vote on who the final winner will be.")
            conversation_id = self._initialise_private_host_conversation(player, host_message)

            #----- Response -----
            public_response_prompt = "This is only shared in the private conversation between you and the Host."
            instruction_override = player.detailed_summaries_string()
            self._private_host_conversation_get_response(player, conversation_id, public_response_prompt, instruction_override)

            #--------- Second message ---------
            host_message = ("So, to remember the drama, can you detail any personal relationship you have with the two finalists? "
                            "Did they ever betray you, ally with you, align with your enemies? We want grudges and memories, so look deep into your memory. "
                            "When you were watching, how did you personally feel about either player? Did they hurt anyone you liked, or maybe got revenge on your behalf?")
            self._private_host_conversation_host_message(conversation_id, host_message)

            public_response_prompt = "Write a detailed recollection of your relationships with both finalists."
            self._private_host_conversation_get_response(player, conversation_id, public_response_prompt, instruction_override)

            host_message = "If the vote were held right now, who are you likely to vote for? On a scale of 1-10, how likely is it that they would change your mind? "
            self._private_host_conversation_host_message(conversation_id, host_message)
            public_response_prompt = "Respond to the host. "
            self._private_host_conversation_get_response(player, conversation_id, public_response_prompt)
            return conversation_id

    def _wake_up_round(self):
        conversation_ids = self._run_tasks([[agent] for agent in self.voting_players], self._wake_up_player_reunion, parallel=True)
        for conv_id in conversation_ids:
            self.gameBoard.close_private_conversation(conv_id)

    def run_vote(self, immunity_players = None):
        #- set up -#
        self.voting_players = list(self.simulationEngine.dead_agents)
        self.finalists = list(self.agents())

        #- action -#
        self._wake_up_round()
        self._host_broadcast("In this last round, our eliminated players will return to cast the final vote to determine the winner of the game.")
        self.competitors_last_statement()
        self._questions_and_answers()
        self.time_to_vote()

    def _reunion_turn(self, agent, user_content_prompt, public_response_prompt, optional=False):
        
        if optional:
            public_response_prompt += " Note: this is an optional turn. If you have nothing to say leave this blank. "
            additional_thought_nudge = "This is an option turn- do you want to speak here? You have to option to leave public response blank."
        else:
            additional_thought_nudge = None
            
        basic_model = DynamicModelFactory.create_model_(agent, "basic_turn", public_response_prompt=public_response_prompt, 
                                                        additional_thought_nudge=additional_thought_nudge )
        result = agent.take_turn_standard(user_content_prompt, self.gameBoard, basic_model)
        
        if not result.public_response:
            print("BEEP BEEP")
            self.private_system_message(agent, "You declined to say anything on this turn. ", )
        else:
            self.gameBoard.handle_public_private_output(agent, result)

    def _get_highlights(self, player):
        return self.simulationEngine.game_master.create_host_script(
            f"Create a short, brief recap of {player.name} highlights, "
            "in the style of a game host recapping quickly some highs and lows "
            "in the finale of a show, before the winner is announced later. "
            "They haven't won yet- they are in the final two. "
            f"Speak directly to {player.name}. ",
            player.detailed_summaries_string(),
            "This is the players own game summary- use it, but also keep in mind it's from their own perspective. ",
            self._host_current_round_history()
        )

    def competitors_last_statement(self):
        prompt = "Respond to the host, and the other players. "
        player1, player2 = self.finalists[0], self.finalists[1]
        self._host_broadcast(f"Congratulations to our two finalists: {player1.name} and {player2.name}.")

        player_1_highlights = self._get_highlights(player1)
        self._host_broadcast(player_1_highlights)
        self._reunion_turn(player1, "", prompt)

        player_2_highlights = self._get_highlights(player2)
        self._host_broadcast(player_2_highlights)
        self._reunion_turn(player2, "", prompt)

        self._host_broadcast("Finalists- what is the last thing you would like to say to the players before the vote?")
        for agent in self.finalists:
            self._reunion_turn(agent, "", prompt)

    def host_vote_intro(self, voter_name, vote_number, total_votes, vote_counts):
        scores_str = ", ".join([f"{name}: {count}" for name, count in vote_counts.items()])
        max_score = max(vote_counts.values()) if any(vote_counts.values()) else 0
        min_score = min(vote_counts.values()) if any(vote_counts.values()) else 0
        is_tied = max_score == min_score

        if vote_number == 0:
            line = f"{voter_name}, you're up first. Who will you vote for to WIN the competition?"
        elif vote_number == total_votes - 1:
            if is_tied:
                line = f"It all comes down to this. {voter_name}, you hold the deciding vote. The scores are tied at {scores_str}."
            else:
                line = f"Last vote of the night. {voter_name}, step up. The current scores: {scores_str}."
        elif is_tied:
            line = f"We're all tied up. {voter_name}, you're next. Current scores: {scores_str}."
        elif max_score - min_score >= 2:
            line = f"Someone's pulling ahead. {voter_name}, it's your turn. Scores: {scores_str}."
        else:
            line = f"{voter_name}, you're up. Current scores: {scores_str}."

        self._host_broadcast(line)

    def host_vote_response(self, voter_name, voted_for, vote_counts, vote_number, total_votes):
        scores_str = ", ".join([f"{name}: {count}" for name, count in vote_counts.items()])
        max_score = max(vote_counts.values())
        leaders = [name for name, count in vote_counts.items() if count == max_score]
        is_tied = len(leaders) > 1

        if vote_number == 0:
            line = f"{voter_name} votes for... {voted_for}. And we're off. {scores_str}."
        elif vote_number == total_votes - 1:
            line = f"{voter_name} casts the final vote for... {voted_for}."
        elif is_tied:
            line = f"{voter_name} votes for {voted_for}. We're deadlocked! {scores_str}."
        else:
            line = f"{voter_name} votes for... {voted_for}. That puts it at {scores_str}."

        self._host_broadcast(line)

    def _cast_jury_vote(self, juror, finalist_names, deadlock_vote=False):
        if deadlock_vote:
            user_content = "It's a dead tie. You get to pick the winner. Who do you choose?"
        else:
            user_content = (
                f"It is time to cast your vote. "
                f"Vote for one of the finalists: {self.format_list(finalist_names)}. "
                f"Who do you vote for, and why? Please include every detail of personal drama you mentioned in your pre-round conversation with the host. "
            )

        action_fields = self._choose_name_field(
            finalist_names,
            "Vote for the finalist you believe deserves to win. "
        )
        response_model = DynamicModelFactory.create_model_(
            juror,
            model_name="jury_vote",
            action_fields=action_fields
        )
        result = juror.take_turn_standard(user_content, self.gameBoard, response_model)
        self.gameBoard.handle_public_private_output(juror, result)
        return result

    def time_to_vote(self):
        finalist_names = self._names(self.finalists)
        jurors = self.voting_players
        total_votes = len(jurors)

        self._host_broadcast("The time has come to vote, for who you want to win... The Game. ")
        vote_counts = {name: 0 for name in finalist_names}

        for vote_number, juror in enumerate(jurors):
            self.host_vote_intro(juror.name, vote_number, total_votes, vote_counts)
            result = self._cast_jury_vote(juror, finalist_names)
            vote = getattr(result, "target_name", "").strip()
            if vote in finalist_names:
                vote_counts[vote] += 1
                self.host_vote_response(juror.name, vote, vote_counts, vote_number, total_votes)
            else:
                self._host_broadcast(f"{juror.name} cast an invalid vote: '{vote}', skipping.")

        winner_name = self._get_winner(vote_counts)

        scores_str = ", ".join([f"{name}: {count}" for name, count in vote_counts.items()])
        self._host_broadcast(
            f"The jury has spoken. Final tally: {scores_str}. "
            f"The winner of the game is... {winner_name}! Congratulations!"
        )
        losers = [name for name in finalist_names if name != winner_name]
        for loser_name in losers:
            self.eliminate_player_by_name(loser_name)

        winner = self._agent_by_name(winner_name)
        self._reunion_turn(winner, "You just won the game! Give your victory speech. ", "Your victory speech to the group. ")


    def _get_winner(self, vote_counts):
        finalist_names = list(vote_counts.keys())

        if not any(vote_counts.values()):
            self._host_broadcast("No valid votes were cast. The result is a draw.")
            return random.choice(finalist_names)

        max_votes = max(vote_counts.values())
        leaders = [name for name, count in vote_counts.items() if count == max_votes]

        # Clear winner
        if len(leaders) == 1:
            return leaders[0]

        # Tied — break by game score
        self._host_broadcast(
            f"We have a tie! {self.format_list(leaders)} are deadlocked on {max_votes} votes each. "
            f"In this case, the player with the highest game score wins."
        )
        tied_agents = [self._agent_by_name(name) for name in leaders]
        top_scorers = self.get_strategic_players(tied_agents, top_player=True, multiple=True)

        if len(top_scorers) == 1:
            winner = top_scorers[0]
            score = self.gameBoard.agent_scores.get(winner.name, 0)
            self._host_broadcast(f"With a game score of {score}, the tiebreaker goes to {winner.name}!")
            return winner.name

        # Still tied — deadlock vote from the most recently eliminated player
        runner_up = self.voting_players[-1]
        self._host_broadcast(
            f"Unbelievable — scores are tied too! "
            f"In this case, the player who will decide the winner is... {runner_up.name}!"
        )
        result = self._cast_jury_vote(runner_up, leaders, deadlock_vote=True)
        winner_name = getattr(result, "target_name", "").strip()

        if winner_name in leaders:
            return winner_name

        # Invalid deadlock vote — pick randomly
        self._host_broadcast(f"{runner_up.name} has spoiled their vote. We will pick a random winner...")
        return random.choice(leaders)

    def _questions_and_answers(self):
        self._host_broadcast("Finalists- some of our voters remain on the fence- It's time to face some of your voters.")

        question = "Which players, based on the conversation with the host, do you think could have their minds changed? "
        undecided_names = self.simulationEngine.game_master.select_players(
            question, self._host_current_round_history(), self._names(self.voting_players), 3)

        for player_name in undecided_names:
            player = self._agent_by_name(player_name, incl_dead=True)
            if player:
                #------ Ask the question ------
                public_response_prompt = (
                    "You've been identified as a player who could have a question- maybe you could have your mind changed? "
                    "Or maybe you're more irate- its more of a statement. "
                    "Now is your chance to put something to one of the finalists and get a response."
                )
                user_content = "Direct a question or statement to one of the finalists."
                additional_thought_nudge = "What could you ask that would change your mind? What would cause the most drama? "
                result = self._ask_directed_question(player, self._names(self.finalists), user_content, public_response_prompt, additional_thought_nudge)

                #--------Get some answers ------
                chosen_name = getattr(result, GamePromptLibrary.model_field_choose_name, None)
                if chosen_name:
                    chosen_agent = self._agent_by_name(chosen_name.strip())
                    if chosen_agent:
                        self._reunion_turn(chosen_agent, "", f"Respond to {player_name}'s question. Directly say anything else you want to say.")
                        self._reunion_turn(player, "", "Anything else to add?", optional=True)
