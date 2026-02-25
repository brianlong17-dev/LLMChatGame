from concurrent.futures import ThreadPoolExecutor
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
import random

class GamePrisonersDilemma(GameMechanicsMixin):
                
    def run_game_prisoners_dilemma_choose_partner(self):
       self.run_game_prisoners_dilemma(choose_partner = True)
       
    def run_game_prisoners_dilemma_choose_partner_winner(self):
       self.run_game_prisoners_dilemma(choose_partner = True)
    
    def run_game_prisoners_dilemma_choose_partner_loser(self):
       self.run_game_prisoners_dilemma(choose_partner = True, winner_picks_first = False)
    
    def get_split_or_steal(self, player, opponent):
        #return player.split_or_steal(self.gameBoard, opponent)
        user_content = GamePromptLibrary.pd_game_prompt.format(opponent_name=opponent.name)
        #-----------------------------
        choices = ["split", "steal"]
        action_fields = self.create_choice_field("action", choices)
        additional_thought_nudge="What points are available? How will the next elimination work? Do you need points or alliance?" 
        model = DynamicModelFactory.create_model_(player, "split_or_steal", 
                    additional_thought_nudge=additional_thought_nudge, action_fields=action_fields)
        response = player.take_turn_standard(user_content, self.gameBoard, model)
        #-----------------------------
        return response
    
    def _calculate_pd_payout(self, choice0, choice1, name0, name1):
        splitPoints = GamePromptLibrary.pd_split
        bothSteal= GamePromptLibrary.pd_both_steal
        stealPoints = GamePromptLibrary.pd_steal
        choice0 = choice0.strip().lower().replace(".", "")
        choice1 = choice1.strip().lower().replace(".", "")
            
        outcomes = {
            ('split', 'split'): (splitPoints, splitPoints, f"Congratulations {name0} and {name1}. You both SPLIT! "),
            ('steal', 'steal'): (bothSteal, bothSteal, f"OH NO {name0} and {name1}... You both STOLE. "),
            ('steal', 'split'): (stealPoints, 0, f"OH NO! {name0} STOLE from {name1}! "),
            ('split', 'steal'): (0, stealPoints, f"OH NO! {name1} STOLE from {name0}! ")
        }
                                
        # 1. Look up the results
        p0_gain, p1_gain, msg = outcomes.get(
            (choice0, choice1), 
            (0, 0, f"Someone hallucinated a move! No points awarded."))
        return p0_gain, p1_gain, msg
    
    def run_game_prisoners_dilemma(self, choose_partner = False, winner_picks_first = True):
        splitPoints = GamePromptLibrary.pd_split
        bothSteal= GamePromptLibrary.pd_both_steal
        stealPoints = GamePromptLibrary.pd_steal
        intro_message = GamePromptLibrary.prisonersDilemmaIntro(choose_partner, winner_picks_first)
        self.gameBoard.host_broadcast(intro_message)

        # 2. Pairing Logic
        available_agents = list(self.simulationEngine.agents)
        random.shuffle(available_agents)
        pairs, leftover_player = self._generate_pairings(available_agents, choose_partner, winner_picks_first)
       
            
        # Handle the leftover player if there is an odd number of agents
        if leftover_player:
            self.gameBoard.host_broadcast(f"{leftover_player.name} is the odd one out this round! They get to sit back and automatically receive {splitPoints} points\n\n")
            self.gameBoard.append_agent_points(leftover_player.name, splitPoints)

        # 3. Execute the pairings
        for agent0, agent1 in pairs:
            self.gameBoard.host_broadcast(f"{agent0.name} vs {agent1.name}. Split or Steal?\n")

            # 1. Get decisions (Blindly)
            with ThreadPoolExecutor() as executor:
                future_result_1 = executor.submit(self.get_split_or_steal, agent0, agent1)
                future_result_2 = executor.submit(self.get_split_or_steal, agent1, agent0)
                results = [future_result_1.result(), future_result_2.result()]

            # 2. Process feedback and sanitize choices in one go
            choices = []
            for agent, res in zip((agent0, agent1), results):
                self.publicPrivateResponse(agent, res)
                choices.append(res.action.strip().lower())
            
            # 1. Look up the results
            p0_gain, p1_gain, msg = self._calculate_pd_payout(choices[0], choices[1], agent0.name, agent1.name)
            
            # 2. Update points and broadcast
            for agent, gain in zip((agent0, agent1), (p0_gain, p1_gain)):
                self.gameBoard.append_agent_points(agent.name, gain)

            result_host_message = f"{msg}{agent0.name} receives {p0_gain}, and {agent1.name} receives {p1_gain} points."
            self.gameBoard.host_broadcast(f"{result_host_message}\n")

            # --- GATHER REACTIONS ---
            for agent in (agent0, agent1):
                reaction = self.respond_to(agent, result_host_message)
                self.publicPrivateResponse(agent, reaction)
                
                
    
    