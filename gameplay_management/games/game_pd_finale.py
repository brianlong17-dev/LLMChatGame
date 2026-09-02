from gameplay_management.games.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.human_turn_form import HumanInputDescription
from pydantic import Field


class GamePrisonersDilemmaFinale(GamePrisonersDilemma):

    sfx = "Respond as yourself. Do not repeat or mirror what your opponent just said."
    
    @classmethod
    def display_name(cls, cfg):
        return "Split or Steal"

    @classmethod
    def is_finale(cls):
        return True

    @classmethod
    def rules_description(cls, cfg):
        return f"Last chance to win- or to share the victory. "

    #####################
    #   Dialog   #
    #####################
    def tie_rules_string_technical(self):
        return ("Game points:\n"
            f"Both Split: Both win.\n"
            f"Both steal:  Both lose.\n"
            f"You Steal | They Split : Only you win.\n"
            f"You Split | They Steal : Only they win.\n"
        )

    def points_rules_string_technical_plus(self, player, opponent):
        cfg = self.cfg
        name = opponent.name
        you = self.game_board.get_agent_score(player.name)
        them = self.game_board.get_agent_score(opponent.name)

        def final(you_gain, them_gain):
            return f"Final score: You: {you + you_gain}. {name}: {them + them_gain}."

        return ("Game points:\n"
            f"Both Split: Both get +{cfg.pd_points_split}. {final(cfg.pd_points_split, cfg.pd_points_split)}\n"
            f"Both Steal: Both only get +{cfg.pd_points_both_steal}. {final(cfg.pd_points_both_steal, cfg.pd_points_both_steal)}\n"
            f"You steal | They trust and Split: You get +{cfg.pd_points_steal} | They get 0. {final(cfg.pd_points_steal, 0)}\n"
            f"You trust and Split | They Steal: You get 0 | They get +{cfg.pd_points_steal}. {final(0, cfg.pd_points_steal)}\n"
        )

    def _human_pre_game_exchange_description(self, is_tie):
        if is_tie:
            return HumanInputDescription(
                titles={"public_response": "You're tied going in. What do you say?"},
                placeholders={"public_response": "trust them?"},
            )
        return HumanInputDescription(
            titles={"public_response": "The final. Anything to say to your opponent?"},
            placeholders={"public_response": "what do you want to say?"},
        )

    def _human_pre_game_exchange_2_description(self):
        return HumanInputDescription(
            titles={"public_response": "Your last word before the game"},
            placeholders={"public_response": "one last word?"},
        )

    def _pre_game_exchange(self, player, is_tie = False):
        game_logic_fields = {
            "goal": (str, Field(description="What is the outcome you want?")),
            "can_you_win": (str, Field(description="There is only one game left. Is it possible for you to win on final scores? Is it possible for you to lose?")),
            "method": (str, Field(description="Do you need to influence your opponent for your goal? If so, how?")),
        }
        opponent = self._other_agents(player, self.agents)[0]
        reminder = self.points_rules_string_technical_plus(player, opponent) if not is_tie else self.tie_rules_string_technical()
            
        self.turn_manager.take_turn(player,
            turn_prompt=f"{reminder}\n\n"
                "Welcome to the final! React to how you feel to be here with your opponent.\n",
            public_response_prompt=f"Speak your mind or play it coy? Last moments of the game. {self.sfx}",
            game_logic_fields=game_logic_fields,
            broadcast=True,
            is_reply = True,
            thinking = False,
            use_higher_model=True,
            human_input_description_object=self._human_pre_game_exchange_description(is_tie))
        
    def _pre_game_exchange_2(self, player, is_coronation=False, is_tie = False):
        coronation_string = "If you have nothing new to add, keep it brief. " if is_coronation else ""
        opponent = self._other_agents(player, self.agents)[0]
       
        self.turn_manager.take_turn(player,
            turn_prompt=f"Read {opponent.name}'s last message. "
                        "This is your final response before the reveal. "
                        f"React to what they said. Do not reveal your choice.\n ",
            public_response_prompt=f"Your last word before the game. Play it however you want. {coronation_string} {self.sfx}",
            game_logic_fields={"method": (str, Field(description="Do you want to influence your opponent? If so, how?"))},
            broadcast=True,
            is_reply = True,
            human_input_description_object=self._human_pre_game_exchange_2_description())

    def _result_react(self, agent, turn_prompt, public_response_prompt, human_input_description_object=None):
        self.turn_manager.respond_to(agent,
            turn_prompt,
            public_response_prompt=public_response_prompt,
            is_reply=True,
            broadcast=True,
            human_input_description_object=human_input_description_object)

    #####################
    #   Split / Steal   #
    #####################
    
    def finale_reg_split_or_steal(self, player, tie_possible):
        tie_string = "If you end on equal points, you may share the crown. Otherwise: " if tie_possible else ""
        mask_slip = "Their choice is already locked in. You can drop any pretense you may have had. Reveal your choice and let them know. " if not tie_possible else ""
        
        turn_prompt_post = ( f"{tie_string}" 
            f"The player with the most points wins, and the loser is evicted. ")
        opponent = self._other_agents(player, self.agents)[0]
        turn_prompt = (
            f"The finale. You are facing {opponent.name}.\n"
            f"You have {self.game_board.agent_scores[player.name]} points. Your opponent has {self.game_board.agent_scores[opponent.name]} points. \n{self.sfx}"
            f"{turn_prompt_post}\n"
            f"{mask_slip}"
        )
        additional_thought_nudge = "The end of your journey, what do you want your decision to be?"
        
        public_response_prompt = f"What do you say as you reveal your choice? From your own logic and feelings, express why you chose this. {mask_slip}"
        
        result = self.get_split_or_steal(player, turn_prompt, public_response_prompt= public_response_prompt, additional_thought_nudge=additional_thought_nudge)
        self._widget_update_entry(player.name, state="picked")
        return result
    
    def finale_tie_split_or_steal(self, player):
        opponent = self._other_agents(player, self.agents)[0]
        turn_prompt = (
            f"The finale. You are facing {opponent.name}.\n"
            f"SPLIT: You both share the crown as co-champions.\n"
            f"STEAL: If only you steal, you are the sole champion and they go home with nothing. If you both steal, you both lose.\n"
            f"Do you trust {opponent.name}? Do you share the crown, or do you go for it all?"
        )
        additional_thought_nudge = "What has your journey with this person been like? Do you trust them? Is shared glory enough, or do you want it all for yourself?"
        public_response_prompt = f"What do you say as you reveal your choice? Your final words to the audience and your opponent. {self.sfx}"
        response = self.get_split_or_steal(player, turn_prompt, public_response_prompt, additional_thought_nudge)
        self._widget_update_entry(player.name, state="picked")
        return response
    
    
    #####################
    #   Handle outcome  #
    #####################
    
    
    def _process_choices(self, agent0, agent1, results):
        choices = []
        for agent, res in zip((agent0, agent1), results):
            choice = res.action
            widget = self._build_widget_update_entry(agent.name, state="revealed", choice=choice)
            self.turn_manager._output_response(agent, res, pre_message_choice_reveal="action", is_reply=True, widget=widget)
            choices.append(choice)

        return choices
   
    def _process_tie_results(self, choice0, choice1, agent0, agent1):
        if choice0 == 'split' and choice1 == 'split':
            self._double_win()
            #TODO push double gold
        elif choice0 == 'steal' and choice1 == 'steal':
            self._double_loss()
            #do nothing?
        else:
            winner, loser = (agent0, agent1) if choice0 == 'steal' else (agent1, agent0)
            #TODO push single red
            self._one_winner_from_tie(winner, loser)
            
    def _double_win(self):
        self._host_broadcast("WE CAN'T BELIEVE IT! A DOUBLE WIN! The air is absolutely electric- after all of the highs and lows, trust wins the day- the ultimate gamble, "
                "and the ultimate reward. GIVE IT UP FOR OUR WINNERS! Tell us, how does this moment feel? ")
        for agent in self.agents:
            self._result_react(agent, 
            "You are a co-champion. You both split. You won together! This is your final turn to say everything you have left to say, and to celebrate your win! ",
            "How does it feel? What do you say to your co-champion and to everyone watching? LETS MAKE IT BIG !!! WOOHOO!!!",
            self._human_result_description("You both won! What do you say?", "celebrate!"))
        self.game_board.game_over = True
        
    def _double_loss(self):
        self._host_broadcast("After everything- neither player wins. Was it greed? Was it spite? Will we ever really know? Did you both just hate the other more than you loved yourself? ")
        # snapshot self.agents because _eliminate_player mutates it mid-loop
        for agent in list(self.agents):
            self._result_react(agent,
            "You both stole. Neither of you won. It's over. This is your final turn, these are your final words. What do you have to say?",
            "You came so close. What do you say on your final turn?",
            self._human_result_description("You both lost. Final words?", "..."))
            self._eliminate_player(agent)
            
    def _one_winner_from_tie(self, winner, loser):
        self._host_broadcast(f"That means we finally have our winner! *{winner.name.upper()}*!")
       
        
        self._host_broadcast(f"Now to our champion, who did it against all odds, at the last moment to secure the win! {winner.name}, was it worth it? To exploit the trust of {loser.name} to become the sole champion?")
        self._result_react(winner,
            f"You stole. {loser.name} split. You are the sole champion. Victory! This is your final turn! Lay it all on the table! YOU WIN! ",
            f"You took the crown from {loser.name}. Was it worth it? What do you say to them and to everyone watching? YOU WON!!",
            self._human_result_description("You took the crown. What do you say?", "was it worth it?"))
        
        loser_question =(f"But now, we must go our darling loser, to {loser.name}- our hearts are broken for you- so close, and to have snatched defeat from the jaws of victory. "
                         "Shock, awe, acceptance? What is going through your mind? Do you have any final words?")
        self._host_broadcast(loser_question)
        self._result_react(loser,
            f"You split. {winner.name} stole. You trusted them and they took the crown from you. You go home with nothing. Your final turn: what do you say?",
            f"You were betrayed at the last moment by {winner.name}. What do you say to them and to everyone else watching?",
            self._human_result_description("You were betrayed. Final words?", "..."))

        self._evict_and_crown(winner, loser)
         
    def _one_winner_reg(self, winner, loser, commentary = "", is_upset = False):
        
        if is_upset:
            winner_msg = (f"In a result NO ONE saw coming... Our winner is *{winner.name.upper()}*!")
            loser_question = f"This is an utter shock - no one can quite believe it. Least of all, {loser.name}, who almost had it all- {loser.name}, how are you feeling right now?"
        else:
            winner_msg = (f"That means we finally have our winner! *{winner.name.upper()}*!")
            loser_question = f"Well now, we must go to {loser.name}. Although you couldn't quite get across the finish line you played an incredible game today. How do you feel? Do you have any final words?"
        
        self._host_broadcast(winner_msg)
        commentary = f"Respond to what happened in the game: {commentary}"
        
        
        winner_q = "What a finish, what was going through your head at that last game?"
        self._host_broadcast(f"Now to our champion, at last- what you've been playing for all along- {winner.name} is our champion! {winner_q}" )
        self._result_react(winner,
            f"You are the sole champion. Victory! This is your final turn! Lay it all on the table! YOU WIN! ",
            f"{commentary}. Respond to host question: {winner_q}. What do you say to your vanquished competitors and to everyone watching? YOU WON!! {self.sfx}",
            self._human_result_description("You win! What do you say?", "your victory speech"))
        
        self._host_broadcast(loser_question)
        self._result_react(loser, 
            f"You were beaten by {winner.name}. {commentary}. Then the host's question: {loser_question}.",
            f"Respond to the final game and the host's question. Afterwards you can give your final thoughts and words to everyone. {self.sfx}",
            self._human_result_description("You lost. Final words?", "your farewell"))
        
        self._evict_and_crown(winner, loser)
    
    #####################
    #  Utils            #
    #####################
    
    def _is_tie(self, agent0, agent1):
        return self._agent_score(agent0.name) == self._agent_score(agent1.name)

    def get_leader(self):
        return max(self.agents, key=lambda a: self._agent_score(a.name))
        
    def _eliminate_player(self, loser):
        host_message = self.cfg.pre_eviction_message.format(victim_name=loser.name.upper())
        self.game_board.host_broadcast(host_message)
        self.simulationEngine.eliminate_player(loser)
        
    def _evict_and_crown(self, winner, loser):
        self._eliminate_player(loser)
        final_q = (f"{winner.name}, how does it feel to be champion? What did you learn from the competition? What advice would you give to yourself if you had to start the game from scratch?")
        if not winner.is_human():
            self._host_broadcast(final_q)
            self._result_react(winner, f"React to host message: {final_q}", "Say how you feel to finish with the crown! ")
       
    #####################
    #  Run              #
    #####################
    
    def _init_widget(self):
        self._widget_pairs = []
        self._add_pair_to_widget(self.agents[0], self.agents[1])
        
           
    def run_game(self):
        agent0 = self.agents[0]
        agent1 = self.agents[1]
        is_tie = self._is_tie(agent0, agent1)
        if is_tie:
            self.run_tie(agent0, agent1)
        else:
            self.run_reg_game(agent0, agent1)
            
        self._host_broadcast("The end! ")
    
    def run_reg_game(self, agent0, agent1):
        self._init_widget()
        tie_threshold = self.cfg.pd_points_steal
        diff = abs(self._agent_score(agent0.name) - self._agent_score(agent1.name))
        tie_possible = (diff == tie_threshold)
        is_coronation = diff > tie_threshold
        
        leader = self.get_leader()
        follower = agent1 if leader is agent0 else agent0
        
        self._host_broadcast(self._reg_intro(is_coronation, tie_possible, leader))
        for player in self.agents:
            self._pre_game_exchange(player)
        for player in self.agents:
            self._pre_game_exchange_2(player, is_coronation)
        if not tie_possible:
            for player in self.agents:
                player._mask_drop=True
        self._host_broadcast(f"Ok let's go- a nation holds its breath- {self.format_list(self._names(self.agents))} ... please reveal your choice.")
        results = self._run_tasks([(agent, tie_possible) for agent in self.agents], self.finale_reg_split_or_steal)

        choices = self._process_choices(agent0, agent1, results)
        result_msg, results_widget = self._process_results_and_points(choices[0], choices[1], agent0, agent1)

        if self._is_tie(agent0, agent1):
            commentary = f"This means {follower.name} has leapt into a tie for first place! "
            self._host_broadcast(f"{result_msg} {commentary}", widget=results_widget)
            self.run_tie(agent0, agent1, is_second_game = True)

        else:
            for player in self.agents:
                player._mask_drop=True
            winner = self.get_leader()
            loser = agent1 if winner is agent0 else agent0
            is_upset = (winner == follower)
            commentary = self._regular_game_commentary(agent0, winner, loser, choices, is_coronation, is_upset)

            if is_upset:
                self._host_broadcast(f"{commentary}", widget=results_widget)
            else:
                self._host_broadcast(f"{result_msg}\n{commentary}", widget=results_widget)
            self._one_winner_reg(winner, loser, commentary, is_upset)
            
    def run_tie(self, agent0, agent1, is_second_game = False):
        self._init_widget()
        self._host_broadcast(self._get_tie_intro(is_second_game))
        for player in self.agents:
            self._pre_game_exchange(player, is_tie = True)
        for agent in self.agents:
            self._pre_game_exchange_2(agent, is_tie = True)
        for player in self.agents:
            player._mask_drop=True
        self._host_broadcast(f"Ok let's go- a nation holds its breath- {self.format_list(self._names(self.agents))} ... please reveal your choice.")
        results = self._run_tasks([(agent,) for agent in self.agents], self.finale_tie_split_or_steal)
        #results = [self.finale_tie_split_or_steal(agent) for agent in self.agents]
        choices = self._process_choices(agent0, agent1, results)
        _, _, msg = self._calculate_pd_payout(choices[0], choices[1], agent0.name, agent1.name)
        
        self._host_broadcast(msg)
        self._process_tie_results(choices[0], choices[1], agent0, agent1)
    
    #####################
    #  Host Scripts     #
    #####################
                 
    def _get_tie_intro(self, is_second_game):
        if is_second_game:
            intro = "We have landed in a tie- that means one final game to determine the winner. "
        else:
            intro = ("Wow- in the finale and we have a TIE. "
                "After everything you've been through, the crown is within reach. "
                "Well... we have a bit of a twist. ")
                
        rules =  ("Once again you will have the chance to split or steal- but you will be playing for the crown. \n\n"
        "If you split, we will have two champions today. Both of you will win. And if you both steal? Well then, you both lose. "
        "However, if only one player steals- they will be our reigning champion alone, while the other goes home empty-handed. \n\n"
        "After everything you've been through, with nothing left to lose- can you finally trust each other and share the victory? \n"
        "Will it be salted earth, shared glory, or one last thorn in the side?\n\n"
        "A double win is on the table- all it requires is a double *trust*. Do you have it in you?")
        return f"{intro}{rules}"
    
    def _reg_intro(self, is_coronation, tie_possible, leader):
        intro =  (f"Our two finalists stand here before us: {self.format_list(self._names(self.agents))}.\n\n")
        points_rules = "If you both split each player gets 3 points. Both steal- each player gets 1 point. If only one player steals, they get 5 points while their opponent gets 0. "
        if is_coronation:
            intro += (f"With {leader.name}'s score so far ahead, it seems the outcome is a foregone conclusion. "
            "This game is a matter of sportsmanship- will you Split as a sign of respect, or Steal to the last? ")
        elif tie_possible:
            intro += (f"One last Prisoner's Dilemma. {points_rules} \nIt is possible that you both end up on the same score! In that case, we have the possibility of a tie - a double win. ")
        else: 
            intro += (f"The game works as before. {points_rules}"
            "The player with the most points will win, while the loser will be our final evictee. ")
            
        return intro
     
    def _regular_game_commentary(self, agent0, winner, loser, choices, is_coronation, is_upset = False):
        commentary = ""
        if is_upset:
            commentary = f"DEAR ME! {winner.name} has *STOLEN* from {loser.name}. They have taken the crown, against all odds at the very last moment. "
        else:       
            winner_choice = choices[0] if winner is agent0 else choices[1]
            loser_choice = choices[1] if winner is agent0 else choices[0]
            
            if winner_choice == 'split' and loser_choice == 'split':
                commentary = "How beautiful - in the last moment, a show of solidarity between our two greatest players. "
            elif winner_choice == 'steal' and loser_choice == 'steal':
                commentary = "Alas... a double steal to close the night. Two bitter foes, bitter til the very end! "
            
            elif winner_choice == 'steal':
                if is_coronation:
                    commentary = f"{winner.name} took every last point until the very end! No mercy, no closing of the gap, only relentless victory! "
                else:
                    #its not an upset
                    commentary = f"{winner.name} secures their lead, taking it EVEN further. Some people really do have it all!"

            elif winner_choice == 'split':
                commentary = f"{loser.name} never gave up- Did {loser.name} try to claw the last remaining points, or did {winner.name} simply want {loser.name} to feel the glow of victory? "
            
        return commentary
     