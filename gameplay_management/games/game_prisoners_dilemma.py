from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary

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

    def _prisoners_dilemma_intro(self):
        pairing_string = self.pairing_method_string(self.cfg())
        points_rules_string = self.points_rules_string()
        return (
            f"It's time to play: Prisoner's Dilemma. "
            f"{pairing_string}\n"
            f"In each pairing you get a choice: SPLIT or STEAL. "
            f"{points_rules_string}\n\n"
        )
        
    def points_rules_string(self):
        cfg = self.cfg()
        pd_split=cfg.pd_points_split
        pd_steal=cfg.pd_points_steal
        pd_both_steal=cfg.pd_points_both_steal
        points_str = (
            f"Co-operate and split for {pd_split} points each- or steal for the chance to win {pd_steal}, while the splitter gets 0. If you both steal, {self.points_string(pd_both_steal)} each. ")
        return points_str
    
    def points_rules_string_technical(self):
        cfg = self.cfg()
        return (
            f"Split | Split : {cfg.pd_points_split} - {cfg.pd_points_split}\n"
            f"Steal | Split : {cfg.pd_points_steal} - 0\n"
            f"Steal | Steal : {cfg.pd_points_both_steal} - {cfg.pd_points_both_steal}\n"
            f"Steal: {cfg.pd_points_steal} or {cfg.pd_points_both_steal}. Split: {cfg.pd_points_split} or 0."
        )

    
    def _choose_partner(self, chooser, available_agents):
        available_agents_names = self._names(available_agents)
        user_content = (
            f"You get to choose who you want to play with from the following list: {available_agents_names}.\n"
            f"Based on your history and the current game context, who do you choose to partner up with for the next mini-game and why? "
        )
        action_fields = self.turn_manager._choose_name_field(available_agents_names, "The exact name of the agent to PAIR UP WITH. ")
        public_response_prompt = (f"After your choice has been revealed what do you say? Why did you pick them, and what do you want to say to them? "
        "This is your chance to convince them to split. Keep it brief. ")
        
        response = self.turn_manager.take_turn(chooser, user_content,  public_response_prompt=public_response_prompt, 
                                  action_fields=action_fields, broadcast = True, is_reply = True)
        
        
        partner_name = self.turn_manager._get_target_name_from_response(response)
        return self._agent_by_name(partner_name)
        
    

    def get_split_or_steal(self, player, opponent):
        user_content = ( #This is a bit excessive but it works.
            f"Prisoner's Dilemma. You are paired with {opponent.name}.\n"
            f"Remember:\n {self.points_rules_string_technical()}"
            f"Based on your game history and personality, make your choice."
        )
        
        choices = ["split", "steal"]
        action_fields = self.turn_manager.create_choice_field("action", choices)
        additional_thought_nudge="What points are available? How will the next elimination work? Do you need points or alliance?"
        public_response_prompt = "A one liner, for AFTER your result has been revealed. (Not neccessary to re-state your choice as it will already be revealed.)."
        return self.turn_manager.take_turn(player, user_content= user_content, additional_thought_nudge=additional_thought_nudge, 
                                    action_fields=action_fields, 
                                    public_response_prompt = public_response_prompt,
                                    broadcast = False)

    def _calculate_pd_payout(self, choice0, choice1, name0, name1):
        cfg = self.cfg()
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
            future0 = executor.submit(self.get_split_or_steal, agent0, agent1)
            future1 = executor.submit(self.get_split_or_steal, agent1, agent0)
            results = [future0.result(), future1.result()]

        choices = []
        for agent, res in zip((agent0, agent1), results):
            self.gameBoard.handle_public_private_output(agent, res, is_reply = True, pre_string = f"*{res.action.upper()}*")
            choices.append(res.action)

        p0_gain, p1_gain, msg = self._calculate_pd_payout(choices[0], choices[1], agent0.name, agent1.name)

        for agent, gain in zip((agent0, agent1), (p0_gain, p1_gain)):
            self.gameBoard.append_agent_points(agent.name, gain)

        result_host_message = f"{msg}{agent0.name} receives {p0_gain}, and {agent1.name} receives {p1_gain} points."
        self._host_broadcast(f"{result_host_message}\n")

        
        if (choices[0] == 'steal' and choices[1] == 'steal'):
            reactions = self._run_tasks([(agent0, result_host_message), (agent1, result_host_message)], 
                                        self.respond_to_return_sender)
            for reaction in reactions:
                self.gameBoard.handle_public_private_output(reaction[0], reaction[1], is_reply = True)
            
        elif (choices[0] != choices[1]):
            for agent in (agent0, agent1):
                reaction = self.turn_manager.respond_to(agent, result_host_message)
                self.gameBoard.handle_public_private_output(agent, reaction, is_reply = True)
    
    def respond_to_return_sender(self, agent, msg):
        return (agent, self.turn_manager.respond_to(agent, msg))
    
    def _execute_pairs(self, pairs):
        for agent0, agent1 in pairs:
            self._execute_pair(agent0, agent1)
            
    

    def _opening_message(self):
        self._host_broadcast("Any last words to share with the group before we play? ")
        for agent in self.agents():
            others = self._names(self._other_agents(agent, self.agents()))
            others_names = self.format_list(others)
            user_content = (f"Each player plays each player- you will face off against both {others_names} (and they will play each other). \n"
            f"BEFORE YOU PLAY- You have the opportunity to strategise- Trick a player into splitting? Really arrange to split? Turn the tables two on one? \n"
            f"Remember: {self.points_rules_string_technical()}")
            additional_thought_nudge = "Is there any advanced strategy you could try here? Or simply share pleasentries. "
            public_response_prompt = f"What will you say to {others_names}? Keep it brief, and to strategy. "
            self.turn_manager.take_turn(agent, user_content= user_content, additional_thought_nudge=additional_thought_nudge, 
                                        public_response_prompt = public_response_prompt,
                                        broadcast = True,
                                        is_reply = True)
    
    def run_game(self):
        #self.widget_dictionary = {pairs = [], scores = []} #name, score, color #TODO
        
        intro_message = self._prisoners_dilemma_intro()
        self._host_broadcast(intro_message)
        
        available = self._shuffled_agents()
        
        cfg=self.cfg()
        choose_partner = cfg.pd_pairing_method in (cfg.pd_pairing_choice_random, cfg.pd_pairing_choice_lowest)
        if cfg.pd_pairing_method == cfg.pd_pairing_choice_all:
            self._opening_message()
        
        if not choose_partner:
            if cfg.pd_pairing_method == cfg.pd_pairing_choice_all:
                pairs = list(combinations(available, 2))
                leftover = None
            else:
                pairs, leftover = self._generate_random_pairings(available)

            if leftover:
                self._award_leftover(leftover)

            self._execute_pairs(pairs)
        
        
        else:
            
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
                self._execute_pair(chooser, partner, nested_host_announcement = True)
                
            if available:
                self._award_leftover(available[0])
                
                
    def _award_leftover(self, leftover):
        auto_points = self.cfg().pd_odd_player_auto_points
        self._host_broadcast(f"{leftover.name} is the odd one out this round! They automatically receive {auto_points} points.\n\n")
        self.gameBoard.append_agent_points(leftover.name, auto_points)
        
            
