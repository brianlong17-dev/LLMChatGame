from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from gameplay_management.human_turn_form import HumanInputDescription

class GamePrisonersDilemma(GameMechanicsMixin):

    @classmethod
    def display_name(cls, cfg):
        return "Prisoner's Dilemma"

    @classmethod
    def rules_description(cls, cfg):
        return f"Players will choose to split or steal to win points. {cls.pairing_method_string(cfg)}"
    
    
    #----------- Strings -----------#

    @classmethod
    def pairing_method_string(cls, cfg):
        pairing_method = cfg.pd_pairing_method
        if pairing_method == cfg.pd_pairing_choice_random:
            return "In a random order, players get to choose their partner."
        elif pairing_method == cfg.pd_pairing_choice_lowest:
            return "In order of lowest score, players get to choose their partner."
        elif pairing_method == cfg.pd_pairing_round_robin:
            return "Every player will face every other player once."
        return "Players will be paired randomly."

    def _prisoners_dilemma_intro(self):
        pairing_string = self.pairing_method_string(self.cfg)
        points_rules_string = self.points_rules_string()
        return (
            f"It's time to play: Prisoner's Dilemma. "
            f"{pairing_string}\n"
            f"In each pairing you get a choice: SPLIT or STEAL. "
            f"{points_rules_string}\n\n"
        )
        
    def points_rules_string(self):
        cfg = self.cfg
        pd_split=cfg.pd_points_split
        pd_steal=cfg.pd_points_steal
        pd_both_steal=cfg.pd_points_both_steal
        points_str = (
            f"Co-operate and split for {pd_split} points each- or steal for the chance to win {pd_steal}, while the splitter gets 0. If you both steal, {self.points_string(pd_both_steal)} each. ")
        return points_str
    
    def points_rules_string_technical(self):
        cfg = self.cfg
        #SCAF
        return ("Game points:\n"
            f"Both Split: Both get +{cfg.pd_points_split} points each.\n"
            f"Both Steal: Both only get +{cfg.pd_points_both_steal} points each.\n"
            f"You steal | They trust and Split : You get +{cfg.pd_points_steal} points | They get 0\n"
            f"You trust and Split | They Steal : You get 0 | They get +{cfg.pd_points_steal} points\n"
        )
    
        
    def _game_ledger_message(self, agent0, agent1, choice0, choice1 ):
        if choice0 == choice1:
            return f"{agent0.name} and {agent1.name}: both {choice0}. "
        elif choice0 == 'steal':
            return f"{agent0.name} stole from {agent1.name}. "
        else:
            return f"{agent1.name} stole from {agent0.name}. "
              
    def _pre_game_conversation(self):
        self._host_broadcast("Any last words to share with the group before we play? ")
        for agent in self.agents:
            others = self._names(self._other_agents(agent, self.agents))
            others_names = self.format_list(others)
            turn_prompt = (f"Each player plays each player- you will face off against both {others_names} (and they will play each other). \n"
            f"BEFORE YOU PLAY- You have the opportunity to strategise- Trick a player into splitting? Really arrange to split? Turn the tables two on one? \n"
            f"Remember: {self.points_rules_string_technical()}")
            additional_thought_nudge = "Is there any advanced strategy you could try here? Or simply share pleasantries. "
            public_response_prompt = f"What will you say to {others_names}? "
            self.turn_manager.take_turn(agent, turn_prompt= turn_prompt, additional_thought_nudge=additional_thought_nudge, 
                                        public_response_prompt = public_response_prompt,
                                        broadcast = True,
                                        is_reply = True,
                                        human_input_description_object=self._human_pre_game_description())
    #----------- Game -----------#
    
    def run_game_choose_partner(self, available):
        cfg = self.cfg
        loser_picks_first = cfg.pd_pairing_method == cfg.pd_pairing_choice_lowest
        while len(available) > 1:
            if loser_picks_first:
                chooser = self.get_strategic_players(available, top_player=False)[0]
                available.remove(chooser)
            else:
                chooser = available.pop()#already shuffled
            self._host_broadcast(f"{chooser.name}, who do you pick to partner with for Prisoner's Dilemma? ")
            partner = self._choose_partner(chooser, available)
            available.remove(partner)
            self._add_pair_to_widget(chooser, partner)
            self._execute_pair(chooser, partner, nested_host_announcement = True)

        if available:
            self._award_leftover(available[0])
    
    def run_game(self):
        self._widget_pairs = []
        intro_message = self._prisoners_dilemma_intro()
        self._host_broadcast(intro_message)
        
        available = self._shuffled_agents()
        
        cfg=self.cfg
        choose_partner = cfg.pd_pairing_method in (cfg.pd_pairing_choice_random, cfg.pd_pairing_choice_lowest)
        if cfg.pd_pairing_method == cfg.pd_pairing_round_robin:
            self._pre_game_conversation()
        
        if choose_partner:
            self.run_game_choose_partner(available)
            
        else:
            if cfg.pd_pairing_method == cfg.pd_pairing_round_robin:
                #Round Robin
                pairs = list(combinations(available, 2))
                leftover = None
            else:
                pairs, leftover = self._generate_random_pairings(available)
                
            if leftover:
                self._award_leftover(leftover)
            self._initialise_widget(pairs)
            self._execute_pairs(pairs)


        


    def _human_pre_game_description(self):
        return HumanInputDescription(
            titles={"public_response": "Anything to say before you all face off?"},
            placeholders={"public_response": "make a deal? bluff?"},
            underlines=["you'll play each player"],
        )

    def _human_partner_description(self):
        return HumanInputDescription(
            titles={
                self.TARGET_NAME_FIELD: "Who do you want to pair up with?",
                "public_response": "What do you say to them before the game? Propose a split?",
            },
            placeholders={"public_response": "..."},
        )

    def _human_split_or_steal_description(self):
        return HumanInputDescription(
            titles={"action": "Split or Steal?"},
            underlines=["both choices are revealed at the same time"],
        )

    def _choose_partner(self, chooser, available_agents):
        available_agents_names = self._names(available_agents)
        turn_prompt = (
            f"You get to choose who you want to play with from the following list: {available_agents_names}.\n"
            f"Based on your history and the current game context, who do you choose to partner up with for the next mini-game and why? "
        )
        action_fields = self.turn_manager._choose_name_field(available_agents_names, "The exact name of the agent to PAIR UP WITH. ")
        public_response_prompt = (f"After your choice has been revealed what do you say? Why did you pick them, and what do you want to say to them? "
        "This is your chance to convince them to split. Keep it brief. ")
        
        response = self.turn_manager.take_turn(chooser, turn_prompt,  public_response_prompt=public_response_prompt,
                                  action_fields=action_fields, broadcast = True, is_reply = True,
                                  human_input_description_object=self._human_partner_description())
        
         
        partner_name = self.turn_manager._get_target_name_from_response(response)
        return self._agent_by_name(partner_name)
        
    def get_split_or_steal_default(self, player, opponent):
        turn_prompt = ( 
            f"Prisoner's Dilemma. You are paired with {opponent.name}.\n"
            f"Remember:\n {self.points_rules_string_technical()}"
            f"Based on your game history and personality, make your choice."
        )
        
        additional_thought_nudge="What points are available? How will the next elimination work? Do you need points or alliance?"
        public_response_prompt = "A one liner, for AFTER your result has been revealed. (Not necessary to re-state your choice as it will already be revealed.)."
        result = self.get_split_or_steal(player, turn_prompt, public_response_prompt, additional_thought_nudge)
        self._widget_update_entry(player.name, opponent.name, state="picked")
        return result

    def get_split_or_steal(self, player, turn_prompt, public_response_prompt, additional_thought_nudge = None):
        choices = ["split", "steal"]
        action_fields = self.turn_manager.create_choice_field("action", choices)
        return self.turn_manager.take_turn(player, turn_prompt= turn_prompt, additional_thought_nudge=additional_thought_nudge, 
                                    action_fields=action_fields,
                                    public_response_prompt = public_response_prompt,
                                    broadcast = False,
                                    human_input_description_object=self._human_split_or_steal_description())

    def _calculate_pd_payout(self, choice0, choice1, name0, name1):
        cfg = self.cfg
        splitPoints=cfg.pd_points_split
        stealPoints=cfg.pd_points_steal
        bothSteal=cfg.pd_points_both_steal
        outcomes = {
            ('split', 'split'): (splitPoints, splitPoints, f"Congratulations {name0} and {name1}. You both *SPLIT!* "),
            ('steal', 'steal'): (bothSteal, bothSteal, f"*OH NO* {name0} and {name1}... You both *STOLE.* "),
            ('steal', 'split'): (stealPoints, 0, f"*OH NO!* {name0} *STOLE* from {name1}! "),
            ('split', 'steal'): (0, stealPoints, f"*OH NO!* {name1} *STOLE* from {name0}! ")
        }
        return outcomes[(choice0, choice1)]

    def _execute_pair(self, agent0, agent1, nested_host_announcement = False):
        self._host_broadcast(f"{agent0.name} vs {agent1.name}. Split or Steal?\n", is_reply = nested_host_announcement)

        with ThreadPoolExecutor() as executor:
            future0 = executor.submit(self.get_split_or_steal_default, agent0, agent1)
            future1 = executor.submit(self.get_split_or_steal_default, agent1, agent0)
            results = [future0.result(), future1.result()]

        choices = []
        for agent, opponent, res in ((agent0, agent1, results[0]), (agent1, agent0, results[1])):
            widget = self._build_widget_update_entry(agent.name, opponent.name, state="revealed", choice=res.action)
            self.turn_manager._output_response(agent, res, pre_message_choice_reveal="action", is_reply=True, widget=widget)
            choices.append(res.action)

        result_host_message, results_widget = self._process_results_and_points(choices[0], choices[1], agent0, agent1)
        self._host_broadcast(f"{result_host_message}\n", widget=results_widget)
        
        if self.cfg.pd_get_reactions and (self.cfg.pd_pairing_method != self.cfg.pd_pairing_round_robin):
            if (choices[0] == 'steal' and choices[1] == 'steal'):
                reactions = self._run_tasks([(agent0, result_host_message), (agent1, result_host_message)],
                                            self.respond_to_return_sender)
                for agent, reaction in reactions:
                    self.turn_manager._output_response(agent, reaction, is_reply=True)

            elif (choices[0] != choices[1]):
                for agent in (agent0, agent1):
                    self.turn_manager.respond_to(agent, result_host_message, broadcast=True, is_reply=True)
                    
        self.game_log._push_to_game_ledger(self._game_ledger_message(agent0, agent1, choices[0], choices[1]))     
        
   
    def _process_results_and_points(self, choice0, choice1, agent0, agent1):
        p0_gain, p1_gain, msg = self._calculate_pd_payout(choice0, choice1, agent0.name, agent1.name)

        widget = None
        for agent, opponent, gain in ((agent0, agent1, p0_gain), (agent1, agent0, p1_gain)):
            self.game_board.append_agent_points(agent.name, gain)
            widget = self._build_widget_update_entry(agent.name, opponent.name, points=gain) or widget

        result_host_message = f"{msg}{agent0.name} receives {p0_gain}, and {agent1.name} receives {p1_gain} points."
        return result_host_message, widget

    
    def respond_to_return_sender(self, agent, msg):
        return (agent, self.turn_manager.respond_to(agent, msg, broadcast=False))
    
    def _execute_pairs(self, pairs):
        for agent0, agent1 in pairs:
            self._execute_pair(agent0, agent1)
            


    
    def _award_leftover(self, leftover):
        auto_points = self.cfg.pd_odd_player_auto_points
        self._host_broadcast(f"{leftover.name} is the odd one out this round! They automatically receive {auto_points} points.\n\n")
        self.game_board.append_agent_points(leftover.name, auto_points)
        
    #----------- Widgets -----------#    
      
    def _get_widget_entry(self, active_name, partner_name=None):
        for pair in self._widget_pairs:
            names = {e["name"] for e in pair}
            if active_name not in names:
                continue
            if partner_name and partner_name not in names:
                continue
            return next(e for e in pair if e["name"] == active_name)
        return None
            
    def _build_widget_update_entry(self, active_name, partner_name=None, state=None, choice=None, points=None):

        entry = self._get_widget_entry(active_name, partner_name)
        if entry is None:
            #should we crash? probably not for a widget
            return None

        if state:
            entry["state"] = state
        if choice:
            entry["choice"] = choice
        if points is not None:
            entry["points"] = points
        return self._widget_payload()

    def _widget_update_entry(self, active_name, partner_name=None, state=None, choice=None, points=None):
        payload = self._build_widget_update_entry(active_name, partner_name, state, choice, points)
        if payload is not None:
            self.game_board.game_sink.on_widget_update(payload)
        return

    def _widget_pair_entry_initial(self, pair):
        couple = []
        for agent in pair:
            entry = {"name": agent.name, "state": "waiting"}
            entry["choice"] = None
            entry["points"] = None
            couple.append(entry)
        return couple

    def _widget_payload(self):
        return {"kind": "pd", "pairs": self._widget_pairs}

    def _emit_widget(self):
        self.game_board.game_sink.on_widget_update(self._widget_payload())

    def _initialise_widget(self, pairs):
        self._widget_pairs = [self._widget_pair_entry_initial(pair) for pair in pairs]
        self._emit_widget()

    def _add_pair_to_widget(self, agent0, agent1):
        self._widget_pairs.append(self._widget_pair_entry_initial([agent0, agent1]))
        self._emit_widget()
            
