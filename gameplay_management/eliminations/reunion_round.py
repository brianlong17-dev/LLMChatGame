
import random
from gameplay_management.eliminations.voting_round_base import VotingRoundBase
from pydantic import Field
from concurrent.futures import ThreadPoolExecutor

class FinaleReunionRound(VotingRoundBase):
    
    _WAKEUP = "Wakeup"
    _INTRODUCTION = "Introduction"
    _QA = "Q&A"
    _VOTING = "Voting"
    _SEGMENTS = [_WAKEUP, _INTRODUCTION, _QA, _VOTING]

    @classmethod
    def display_name(cls, cfg):
        return "Reunion"

    @classmethod
    def is_finale(cls):
        return True

    @classmethod
    def rules_description(cls, cfg):
        return "This is a reunion round"

    @classmethod
    def is_private_round(cls):
        return False

    def _wake_up_player_reunion(self, player):
        if player.is_human():
            return None
        
        finalist_names = self.format_list(self._names(self.finalists))
        questions = {}
        questions["public_response"] = (
            "Hey- welcome back to the game. You have been watching since your elimination. "
            "But now you will have a chance to have your say- to air any grievances or settle any scores. "
            "Later in the round, the eliminated players will vote to pick the final winner."
        )
        questions["memories_and_relationships"] = (
            f"Our finalists: {finalist_names}. For both finalists, can you tell your story as it crossed paths with both players? "
            "What were your feelings- the biggest moments. Moments of allyship or betrayal. "
        )
        questions["pre_vote_poll"] = (
            "You will vote later. But if the vote were held right now, who would you vote for to win? "
            "On a scale of 1-10, how likely is it that your mind could be changed?"
        )

        return self._host_back_and_forth(
            player, questions,
            instruction_override=player.detailed_summaries_string()
        )
        
        
    def _wake_up_round(self):
        self._on_segment(self._WAKEUP)
        self.game_board._loading_string("Waking players up")
        agents_to_wake = [[agent] for agent in self.voting_players if not agent.is_human()]
        conversation_ids = self._run_tasks(agents_to_wake, self._wake_up_player_reunion, parallel=True)
        for conv_id in conversation_ids:
            if conv_id: #human - return None
                self.game_board.close_private_conversation(conv_id)
        self.game_board._end_loading()

    def _set_segment_titles(self, segments):
        self.game_board.game_sink.on_segment_titles(segments)
        
    def _on_segment(self, segment):
        self.game_board.game_sink.on_feed_marker(segment)
        
    def run_vote(self):
        
        #- set up -#
        self._set_segment_titles(self._SEGMENTS)
        self.voting_players = list(self.simulationEngine.dead_agents)
        self.finalists = list(self.agents)
        self._initialise_voting_widget(self._names(self.finalists), self._names(self.voting_players))
                                       
        #- action -#
        executor = ThreadPoolExecutor()
        wake_up_future = executor.submit(self._wake_up_round)
                
        self._host_broadcast("In this last round, our eliminated players will return to cast the final vote to determine the winner of the game.")
        self.host_intro_finalists()
        wake_up_future.result()
        executor.shutdown(wait=False) #Wait for wakeup to finish

        self._questions_and_answers()
        
        self._host_broadcast("Finalists- what is the last thing you would like to say to the players before the vote?")
        for agent in self.finalists:
            self.turn_manager.take_turn(agent,
                    f"Respond to the host, and make your final turn before the vote. You can actually sway votes here- listen to the feedback, and think of all voters: {self._dead_agent_names()}",
                    public_response_prompt="Make it count, refer to specific votes. What specific examples can you hit to sway them? (3-4 lines). ",
                    broadcast=True, is_reply=True)
            
        self.time_to_vote()

    def _reunion_turn(self, agent, turn_prompt, public_response_prompt, optional=False, private_thoughts_prompt = None, is_reply = False):
        #TODO depreciate
        if optional:
            public_response_prompt += " Note: this is an optional turn. If you have nothing to say leave this blank. "
            additional_thought_nudge = "This is an optional turn- do you want to speak here? You have the option to leave public response blank."
        else:
            additional_thought_nudge = None
            
        result =  self.turn_manager.take_turn(
            agent, turn_prompt=turn_prompt,
            public_response_prompt=public_response_prompt,
            additional_thought_nudge=additional_thought_nudge, private_thoughts_prompt=private_thoughts_prompt
        )
        if not result.public_response:
            self.private_system_message(agent, "You declined to say anything on this turn. ", )
        else:
            self.turn_manager._output_response(agent, result, is_reply=is_reply)

    def _get_highlights(self, player):
        return self.simulationEngine.game_master.create_host_script(
            f"Create a short, brief recap of {player.name} highlights- MAX 3 LINES -, "
            "in the style of a game host recapping quickly some highs and lows "
            "in the finale of a show, before the winner is announced later. "
            "They haven't won yet- they are in the final two. "
            f"Speak directly to {player.name}. ",
            player.detailed_summaries_string(),
            "This is the players own game summary- use it, but also keep in mind it's from their own perspective. ",
            self._host_current_round_history()
        )
    def _dead_agent_names(self):
        return self.format_list(self._names(self.dead_agents()))
    def host_intro_finalists(self):
        self._on_segment(self._INTRODUCTION)
        player1, player2 = self.finalists[0], self.finalists[1]
        self._host_broadcast(f"Congratulations to our two finalists: {player1.name} and {player2.name}.")

        turn_prompt="Respond to the host - be as grounded as you can- talk about real things that happened. Try to keep to under 5 lines. "
        public_response_prompt=f"Your words which is also being heard by the jury: {self._dead_agent_names()}"
        
        player_1_highlights = self._get_highlights(player1).script
        self._host_broadcast(player_1_highlights, animate_as_player=True)
        self.turn_manager.take_turn(player1, turn_prompt, public_response_prompt=public_response_prompt, broadcast=True, is_reply=True)
       

        player_2_highlights = self._get_highlights(player2).script
        self._host_broadcast(player_2_highlights ,animate_as_player=True)
        self.turn_manager.take_turn(player2, turn_prompt, public_response_prompt=public_response_prompt, broadcast=True, is_reply=True)
       

        

    def host_vote_intro(self, voter_name, vote_number, total_votes, vote_counts):
        scores_str = ", ".join([f"{name}: {count}" for name, count in vote_counts.items()])
        max_score = max(vote_counts.values()) if any(vote_counts.values()) else 0
        min_score = min(vote_counts.values()) if any(vote_counts.values()) else 0
        is_tied = max_score == min_score

        if vote_number == 0:
            line = f"*{voter_name}*, you're up first. Who will you vote for to WIN the competition?"
        elif vote_number == total_votes - 1:
            if is_tied:
                line = f"It all comes down to this. *{voter_name}*, you hold the deciding vote."
            else:
                line = f"Last vote of the night. *{voter_name}*, step up. "
        elif is_tied:
            line = f"We're all tied up. *{voter_name}*, you're next "
        elif max_score - min_score >= 2:
            line = f"Someone's pulling ahead. *{voter_name}*, it's your turn.  "
        else:
            line = f"*{voter_name}*, you're up. "

        self._host_broadcast(line)

    def host_vote_response(self, voter_name, voted_for, vote_counts, vote_number, total_votes):
        scores_str = ", ".join([f"{name}: {count}" for name, count in vote_counts.items()])
        max_score = max(vote_counts.values())
        leaders = [name for name, count in vote_counts.items() if count == max_score]
        is_tied = len(leaders) > 1

        if vote_number == 0:
            line = f"{voter_name} votes for... {voted_for}. And we're off. *{scores_str}.*"
        elif vote_number == total_votes - 1:
            line = f"{voter_name} casts the final vote for... {voted_for}."
        elif is_tied:
            line = f"{voter_name} votes for {voted_for}. We're deadlocked! *{scores_str}.*"
        else:
            line = f"{voter_name} votes for... {voted_for}. That puts it at *{scores_str}.*"

        self._host_broadcast(line)

    def _cast_jury_vote(self, juror, finalist_names, deadlock_vote=False, is_final=False):
        if deadlock_vote:
            turn_prompt = "It's a dead tie. You get to pick the winner. Who do you choose?"
        else:
            turn_prompt = (
                f"It is time to cast your vote. "
                f"Vote for one of the finalists: {self.format_list(finalist_names)}. "
                f"Who do you vote for, and why? Ground your answer in specfific examples- but this is really your space to express your emotional truth. "
            )

        action_fields = self.turn_manager._choose_name_field(
            finalist_names,
            "Vote for the finalist you believe deserves to win. "
        )
        result = self.turn_manager.take_turn(juror, turn_prompt, model_name="jury_vote",
                                             action_fields=action_fields, broadcast=False)
        vote = getattr(result, "target_name", "").strip()
        widget = self._build_voting_widget_update(juror.name, vote, is_final=is_final) if vote in finalist_names else None
        self.turn_manager._output_response(juror, result, post_message_choice_reveal=self.TARGET_NAME_FIELD, is_reply=True,
                                           widget=widget)
        return result

    def time_to_vote(self):
        self._on_segment(self._VOTING)
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
        winner._mask_drop=True
        self._reunion_turn(winner, "You just won the game! Address the group (You can drop any pretense you may have had- the game is over.) ", "Your victory speech to the group. ")


    def _get_winner(self, vote_counts):
        finalist_names = list(vote_counts.keys())

        max_votes = max(vote_counts.values())
        leaders = [name for name, count in vote_counts.items() if count == max_votes]

        # Clear winner
        if len(leaders) == 1:
            self._vote_widget_vote_finalised()
            return leaders[0]

        runner_up = self.voting_players[-1]
        self._host_broadcast(
            f"We have a tie... in this case, one additional vote will be given to our first runner up. "
            f"The player who will decide the winner is... {runner_up.name}!"
        )
        result = self._cast_jury_vote(runner_up, leaders, deadlock_vote=True, is_final=True)
        winner_name = getattr(result, "target_name", "").strip()
        if winner_name in leaders:
            return winner_name

        # Invalid deadlock vote — pick randomly
        self._host_broadcast(f"{runner_up.name} has spoiled their vote. We will pick a random winner...")
        return random.choice(leaders)
    
    
    def _question_intro_script(self, player):
        return self.simulationEngine.game_master.create_host_script(
                    directive = (f"{player.name} is about to confront one of the finalists with a question . "
                        f" You're introducing them, {player.name}. "
                        f"With the knowledge you have from {player.name}'s private conversation with the host, "
                        " - if they have concrete things to mention, mention them briefly in passing. "
                        f" You're the HOST only introducing {player.name}- the finalists have already been introduced. "
                        f" Try to mention a personal detail to {player.name} regarding the finalists if possible. "
                        f" But still - at least feign neutrality. You're still the professional host. "
                        f" Length: A quick 3-4 liner. "
                        ),
                    additional_context = player.detailed_summaries_string(), 
                    context_explanation =
                    f"This is the players history. (You should also see their private conversation with the host in the current round context)" ,
                    game_context = self.game_board.context_builder.current_round_formatted(player),
                    cot_prompts = [f"Explain {player.name}'s personal history with finalists. What sensitive moments in there could be upsetting? Include detail that you could mention when you introduce {player.name} to ask their question. "]
                )

    def _questions_and_answers(self):
        self._on_segment(self._QA)
        self._host_broadcast("Finalists- some of our voters remain on the fence- It's time to face some of your voters.")

        question = "Which players, based on the conversation with the host, would have the most explosive confrontation with either of the finalists? "
        undecided_names = self.simulationEngine.game_master.select_players(
            question, self._host_current_round_history(), self._names(self.voting_players), 3)
        
        #maybe method this 
        voting_human = next((agent for agent in self.voting_players if agent.is_human()), None)
        if voting_human:
            if voting_human.name not in undecided_names:
                undecided_names.append(voting_human.name)
                
        for player_name in undecided_names:
            
            player = self._agent_by_name(player_name, incl_dead=True)
            if player:
                #host intro---
                script = self._question_intro_script(player).script
                self._host_broadcast(script, animate_as_player=True)
                #------ Ask the question ------
                public_response_prompt = (
                    "You are facing the finalist. "
                    "Direct a question or statement to them to get a response. "
                    "Be speficic and to the point - max 3 lines. "
                )
                turn_prompt = "Questions and Answers: Pick a finalist- a question or statement."
                additional_thought_nudge = "What could you ask that would change your mind? What would cause the most drama? "
                result = self.turn_manager._ask_directed_question(
                    player, self._names(self.finalists), turn_prompt, public_response_prompt, additional_thought_nudge, is_reply = True
                )

                #--------Get some answers ------
                chosen_name = self.turn_manager._get_target_name_from_response(result)
                if chosen_name:
                    chosen_agent = self._agent_by_name(chosen_name.strip())
                    if chosen_agent:
                        self._reunion_turn(chosen_agent, "", f"Respond to {player_name}'s question. Be specific supporting your claims. This is your chance to genuinely change minds to win- make it count. Quick answers prefered (max 4 lines). ", is_reply = True)
                        self._reunion_turn(player, f"{chosen_agent.name} has responded to your question. Do you have anything to say in response to their answer? Do not repeat what you said in your question. - Max 2 lines -", "Anything else to add?", 
                                           optional=True, private_thoughts_prompt = "They responded to your question. Did they answer well enough? Do you have anything left to say to them, or to the other voters? You will have another chance to share your mind when you vote. ", is_reply = True)
