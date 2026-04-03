
import random
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory

class FinaleReunionRound(BaseRound):
    
    @classmethod
    def display_name(cls, cfg):
        return "Finale Reunion Round"

    @classmethod
    def rules_description(cls, cfg):
        return "This is a reunion round"
        
        
    def _output_discussion_round_text(self, player, result):
        pass
        #TODO depreciate
        #this is useful because we want to have a private round
        #self.gameBoard.handle_public_private_output(player, result, override = True)
    
    @classmethod
    def is_discussion(cls):
        return False
    
    @classmethod
    def is_private_round(cls):
        return False
    
    def _wake_up_player_reunion(self, player):
            user_content =  ("Hey! We loved you so much in the game! "
                             "It's time for you to come back. "
                             "You're going to get a change to see old friends, confront foes, and let the players know what you think about the game. "
            )
            
            
            #--------- First message -------""
            users = ["Host", player.name]
            conversation_id = self.gameBoard.log_new_restricted_conversation(users, "Host", user_content)
            #----- Response ------ #
            public_response_prompt = "This is only shared in the private conversation between you and the Host."
            basic_model = DynamicModelFactory.create_model_(player, "basic_turn", public_response_prompt = public_response_prompt )
            instruction_override = player.detailed_summaries_string()
            result = player.take_turn_standard(user_content, self.gameBoard, basic_model, instruction_override = instruction_override)
            self.gameBoard.log_message_to_conversation(conversation_id, player.name, result.public_response)
            #-----------------------------------#
            #--------- Second message -------"
            user_content = ("So, to remember the drama, can you detail any personal relationship you have with the two finalists?"
                            "Did they ever beytray you, ally with you, allign with your enemies? We want grudges and memories, so look deep into your memory."
                            "When you were watching, how did you personally feel about either player? Did they hurt anyone you liked, or maybe got revenge on your behalf?")
            self.gameBoard.log_message_to_conversation(conversation_id, "Host", user_content)
            
            public_response_prompt = "Write a detailed recollection of your relationships with both finalists."
            basic_model = DynamicModelFactory.create_model_(player, "basic_turn", public_response_prompt = public_response_prompt)
            result = player.take_turn_standard(user_content, self.gameBoard, basic_model, instruction_override = instruction_override)
            self.gameBoard.log_message_to_conversation(conversation_id, player.name, result.public_response)
            return conversation_id

    def _wake_up_round(self):
        #purely moved to allow it as optional 
        conversation_ids = self._run_tasks([[agent] for agent in self.simulationEngine.dead_agents], self._wake_up_player_reunion)
        for conv_id in conversation_ids:
            self.gameBoard.close_private_conversation(conv_id)
            
    def run_game(self):
        
        self._wake_up_round()
        self.run_finale_intro()
        
        
        self.competitors_last_statement()
        self.reveal_twist()
        self.last_appeal()
        self.time_to_vote() #this is voting for the winner
        
        
    
    def _reunion_turn(self, agent, user_content_prompt, public_response_prompt, private_thoughts_prompt = None, optional = True):
        
        basic_model = DynamicModelFactory.create_model_(agent, "basic_turn", public_response_prompt = public_response_prompt, private_thoughts_prompt = private_thoughts_prompt, optional=optional)
        result = agent.take_turn_standard(user_content_prompt, self.gameBoard, basic_model)
        if optional:
            public_response = result.public_response
            if not public_response:
                print("BEEP BEEP BEEP")
        else:
            public_response = True
            
        if public_response:
            self.gameBoard.handle_public_private_output(agent, result)

    def run_finale_intro(self):
        
        host_string = (f"Eliminated players... welcome back to the arena. "
                       f"Everybody give it up for {self.format_list([agent.name for agent in self.dead_agents()])}")
        self.gameBoard.host_broadcast(host_string)
        host_string = "Welcome back to our eliminated contestants. What do you make of the game since you've been away?"
        self.gameBoard.host_broadcast(host_string)
        for agent in self.simulationEngine.dead_agents:
            prompt = "Respond to the host, and any other players. Directly say anything else you want to say."
            self._reunion_turn(agent, "", prompt, optional = True)
            
    
        self.gameBoard.host_broadcast("Thank you so much for that. ")
        host_string = "To our finalists, is there anything you would like to say in response?"
        self.gameBoard.host_broadcast(host_string)
        for agent in self.agents():
            prompt = "Respond to the host, and to the other players. "
            self._reunion_turn(agent, "", prompt)
        
        
        extra_response = True
        #see how this goes
        if extra_response:
            host_string = "Thank you for that- for our eliminees- anything else to add?"
            self.gameBoard.host_broadcast(host_string)
            for agent in self.simulationEngine.dead_agents:
                prompt = "Respond to the host, and the other players. Directly say anything else you want to say."
                self._reunion_turn(agent, "", prompt, optional = True)
            
            
            
        #"I think it would be cool if the host could put a question to a group of people, they can all respond. "
        #3 points- he can read their agendas - quote them, put it to a group to respond, in order? can we do that
        #maybe stir some drama- all players can respond
        #3 questions drama stirring... i wonder if he could do this with the higher model, or its not worth the wait
        
        
    def competitors_last_statement(self):
        names = self._names(self.agents())
        host_broadcast = f"Congratulations to our two finalist, {names[0]} and {names[1]}. "
        player_1_highlights = ""
        player_2_highlights = ""
        
        self.gameBoard.host_broadcast(f"You've both played an amazing game- {player_1_highlights}, {player_2_highlights}")
        
        self.gameBoard.host_broadcast(f"Looking back, do you have anything to say to the fans at home? " 
                                      "Before the finale, what was your personal highlight? Do you have anything to say to your fellow finalist?")
        
        for agent in self.agents():
            prompt = "Respond to the host, and the other players. "
            self._reunion_turn(agent, "", prompt)
            
        
    def reveal_twist(self):
        host_string = "To our finalist... do you have any guesses about what will happen in the finale? What the final game may be? "
        self.gameBoard.host_broadcast(host_string)
        for agent in self.agents():
            prompt = "Respond to the host "
            self._reunion_turn(agent, host_string, prompt)
            
        host_string = "You may have been wondering why we brought back the eliminated players- it wasn't just for a tearful reunion. "
        self.gameBoard.host_broadcast(host_string)
        host_string = "In fact they are here... to determine your fate. "
        self.gameBoard.host_broadcast(host_string)
        host_string = "The eliminated players will vote for the player they want to WIN the game. The power is BACK in the hands that our finalists have outlasted, and in some cases- sent home. "
        self.gameBoard.host_broadcast(host_string)
        
        for agent in self.agents():
            prompt = "Respond to the plot twist! " #These could all fall flat without more prompting
            self._reunion_turn(agent, "", prompt, private_thoughts_prompt = "What will this mean for the game! For your chances of winning?") #private thought nudge
        
        host_string = "Our ex players-- what do you make of this twist? "
        self.gameBoard.host_broadcast(host_string)
        for agent in self.dead_agents():
            prompt = "Respond to the plot twist! " #These could all fall flat without more prompting
            self._reunion_turn(agent, "", prompt, private_thoughts_prompt = "How will everyone vote?") #private thought nudge
        
        
    def last_appeal(self):
        self.gameBoard.host_broadcast("Finalists... this your last chance. Why should every player vote for you. This is your last chance... to make your play.. and WIN!")
        prompt = "This your last appeal. This is your last change to appeal to each of the voting players. Why should they vote for you?"
        for agent in self.agents():
            self._reunion_turn(agent, "", prompt, optional = False)

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

        self.gameBoard.host_broadcast(line)

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

        self.gameBoard.host_broadcast(line)

    def _cast_jury_vote(self, juror, finalist_names, deadlock_vote = False):
        if deadlock_vote:
            user_content = (
                f"It's a dead tie. You get to pick the winner. Who do you choose?"
        )
        else: 
            user_content = (
                f"It is time to cast your jury vote. "
                f"Vote for one of the finalists: {self.format_list(finalist_names)}. "
                f"Who do you vote for, and why?"
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
        finalist_names = self._names(self.simulationEngine.agents)
        jurors = self.simulationEngine.dead_agents
        total_votes = len(jurors)

        self.gameBoard.host_broadcast("The time has come to vote, for who you want to win... The Game. ")
        vote_counts = {name: 0 for name in finalist_names}

        for vote_number, juror in enumerate(jurors):
            self.host_vote_intro(juror.name, vote_number, total_votes, vote_counts)
            result = self._cast_jury_vote(juror, finalist_names)
            vote = result.target_name.strip()
            if vote in finalist_names:
                vote_counts[vote] += 1
                self.host_vote_response(juror.name, vote, vote_counts, vote_number, total_votes)
            else:
                self.gameBoard.host_broadcast(f"{juror.name} cast an invalid vote: '{vote}', skipping.")



        winner_name = self._get_winner(vote_counts)
        
        scores_str = ", ".join([f"{name}: {count}" for name, count in vote_counts.items()])
        self.gameBoard.host_broadcast(
            f"The jury has spoken. Final tally: {scores_str}. "
            f"The winner of the game is... {winner_name}! Congratulations!"
        )
        losers = [name for name in finalist_names if name != winner_name]
        for loser_name in losers:
            self.eliminate_player_by_name(loser_name)

        winner = self._agent_by_name(winner_name)
        prompt = "You just won the game! Give your victory speech."
        self._reunion_turn(winner, prompt, "Your victory speech to the group.")
    

    def _get_winner(self, vote_counts):
        finalist_names = list(vote_counts.keys())

        if not any(vote_counts.values()):
            self.gameBoard.host_broadcast("No valid votes were cast. The result is a draw.")
            return random.choice(finalist_names)

        max_votes = max(vote_counts.values())
        leaders = [name for name, count in vote_counts.items() if count == max_votes]

        # Clear winner
        if len(leaders) == 1:
            return leaders[0]

        # Tied — break by game score
        self.gameBoard.host_broadcast(
            f"We have a tie! {self.format_list(leaders)} are deadlocked on {max_votes} votes each. "
            f"In this case, the player with the highest game score wins."
        )
        tied_agents = [self._agent_by_name(name) for name in leaders]
        top_scorers = self.get_strategic_players(tied_agents, top_player=True, multiple=True)

        if len(top_scorers) == 1:
            winner = top_scorers[0]
            score = self.gameBoard.agent_scores.get(winner.name, 0)
            self.gameBoard.host_broadcast(
                f"With a game score of {score}, the tiebreaker goes to {winner.name}!"
            )
            return winner.name

        # Still tied — deadlock vote from the most recently eliminated player
        runner_up = self.simulationEngine.dead_agents[-1]
        self.gameBoard.host_broadcast(
            f"Unbelievable — scores are tied too! "
            f"In this case, the player who will decide the winner is... {runner_up.name}!"
        )
        result = self._cast_jury_vote(runner_up, leaders, deadlock_vote=True)
        winner_name = getattr(result, "target_name", "").strip()

        if winner_name in leaders:
            return winner_name

        # Invalid deadlock vote — pick randomly
        self.gameBoard.host_broadcast(
            f"{runner_up.name} has spoiled their vote. We will pick a random winner..."
        )
        return random.choice(leaders)

       
        
        
    def questions_and_answers(self):
        #this is a bit more complex, and i guess we rely on the optional response here-
        #actually a bit of implementation required, but the host could pick the questions?
        #but maybe first we will just pick 3 random
        pass