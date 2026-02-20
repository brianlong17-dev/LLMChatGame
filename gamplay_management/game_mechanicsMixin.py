
from prompts.gamePrompts import GamePromptLibrary
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.player import Debater

class GameMechanicsMixin:
        
    def run_game_prisoners_dilemma_choose_partner(self):
       self.run_game_prisoners_dilemma(choose_partner = True)
       
    def run_game_prisoners_dilemma_choose_partner_winner(self):
       self.run_game_prisoners_dilemma(choose_partner = True)
    
    def run_game_prisoners_dilemma_choose_partner_loser(self):
       self.run_game_prisoners_dilemma(choose_partner = True, winner_picks_first = False)
         
    def run_game_prisoners_dilemma(self, choose_partner = False, winner_picks_first = True):
        splitPoints = GamePromptLibrary.pd_split
        bothSteal= GamePromptLibrary.pd_both_steal
        stealPoints = GamePromptLibrary.pd_steal
        intro_message = GamePromptLibrary.prisonersDilemmaIntro(choose_partner, winner_picks_first)
        self.gameBoard.host_broadcast(intro_message)

        # 2. Pairing Logic
        # Assuming self.simulationEngine.agents is a list of your agent objects. We shuffle to make pairings random.
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

            # 1. Get decisions (Blindly). Ensure agent0 sees agent1 as the opponent and vice versa.
            results = [agent0.split_or_steal(self.gameBoard, agent1), 
                    agent1.split_or_steal(self.gameBoard, agent0)]

            # 2. Process feedback and sanitize choices in one go
            choices = []
            for agent, res in zip((agent0, agent1), results):
                self.publicPrivateResponse(agent, res)
                choices.append(res.action.strip().lower())

            choice0 = choices[0].strip().lower().replace(".", "")
            choice1 = choices[1].strip().lower().replace(".", "")
            
            outcomes = {
                ('split', 'split'): (splitPoints, splitPoints, f"Congratulations {agent0.name} and {agent1.name}. You both SPLIT! "),
                ('steal', 'steal'): (bothSteal, bothSteal, f"OH NO {agent0.name} and {agent1.name}... You both STOLE. "),
                ('steal', 'split'): (stealPoints, 0, f"OH NO! {agent0.name} STOLE from {agent1.name}! "),
                ('split', 'steal'): (0, stealPoints, f"OH NO! {agent1.name} STOLE from {agent0.name}! ")
            }
                                    
            # 1. Look up the results
            p0_gain, p1_gain, msg = outcomes.get(
                (choice0, choice1), 
                (0, 0, f"Someone hallucinated a move! No points awarded.")
            )

            # 2. Update points and broadcast
            for agent, gain in zip((agent0, agent1), (p0_gain, p1_gain)):
                self.gameBoard.append_agent_points(agent.name, gain)

            result_host_message = f"{msg}{agent0.name} receives {p0_gain}, and {agent1.name} receives {p1_gain} points."
            self.gameBoard.host_broadcast(f"{result_host_message}\n")

            # --- GATHER REACTIONS ---
            for agent in (agent0, agent1):
                reaction = agent.respond_to(self.gameBoard, result_host_message)
                self.publicPrivateResponse(agent, reaction)
                
    def run_game_give(self):
        points_amount = 3
        host_intro = (f"Well, enough of the scheming, lying, conning... whatever happened to giving!? "
        f"In this round, you will get to pick a pal. The player you pick will receive {points_amount} points! "
        f"Everyone is happy! Well... except any player with no friends! hehe")
        self.gameBoard.host_broadcast(host_intro)
        available_agents = list(self.simulationEngine.agents)
        random.shuffle(available_agents)
        
        for player in available_agents:
            "pick a player to give points to. This will be a public show- "
            #valid players: gameBoard.agents copyWithout:player
            
            self.gameBoard.host_broadcast(f"{player.name}! You're up- what player are you choosing, and why?")
            context_msg = f"Choose one player from to receive {points_amount} points. Explain why."
            response = player.choose_other_player(self.gameBoard, context_msg)
            self.publicPrivateResponse(player, response)
            friend_name = response.action.strip()
            friend = self._agent_by_name(friend_name)
            
            if not friend or friend.name == player.name:
                result_host_string = f"Oh no! {player.name} tried to give points to '{friend_name}'... but that's an invalid choice! No points."
                player_for_reaction = player 
            else:
                result_host_string = f"Yay! {player.name} chooses {friend.name}! They receive {points_amount} points."
                self.gameBoard.append_agent_points(friend.name, points_amount)
                player_for_reaction = friend
            
            self.gameBoard.host_broadcast(result_host_string)
            reaction = friend.respond_to(self.gameBoard, result_host_string)
            self.publicPrivateResponse(player_for_reaction, reaction)
            
            
    def run_game_steal(self):
        points_amount = 3
        host_intro = (f"Well, it's time to lay down your mark.. "
        f"In this round, you will get to STEAL. Whatever player you pick, you will receive {points_amount} points... and they will LOSE them! "
        f"If you choose a player with less than {points_amount} points, their points wont go below zero, and you won't receive the full {points_amount} points." )
        self.gameBoard.host_broadcast(host_intro)
        available_agents = list(self.simulationEngine.agents)
        random.shuffle(available_agents)
        
        for player in available_agents:
            "pick a player to give points to. This will be a public show- "
            #valid players: gameBoard.agents copyWithout:player
            
            self.gameBoard.host_broadcast(f"{player.name}! You're up- what player are you choosing to steal from, and why?")
            context_msg = (f"Choose one player from to steal {points_amount} points from. Explain why."
            f"If you steal from a player with less than {points_amount}, you'll only get whatever points the have, maybe zero.")
            
            thoughtNudge = (f"Current scores: {self.gameBoard.agent_scores}"
            f"If you try to steal from someone with 0 points, you essentially pass.")
            response = player.choose_other_player(self.gameBoard, context_msg, additional_thought_nudge=thoughtNudge)
            self.publicPrivateResponse(player, response)
            victim_name = response.action.strip()
            friend = self._agent_by_name(victim_name)
            
            if not friend or friend.name == player.name:
                result_host_string = f"Oh no! {player.name} tried to steal points from '{victim_name}'... but that's an invalid choice! No points."
                player_for_reaction = player 
            else:
                current_victim_points = self.gameBoard.agent_scores.get(victim_name, 0)
                actual_steal = min(points_amount, current_victim_points)
                if actual_steal == 0:
                    result_host_string = (f"{player.name} passes on this turn by choosing a player with no points. No one loses any points, and they don't receive any!"
                    f"{player.name}, you chose a player with 0 points, meaning your turn passes. What was your thought proccess behind this move?")
                    player_for_reaction = player 
                else:
                    result_host_string = (f"Oooooh! {player.name} choose to steal from {friend.name}! "
                    f"They receive {actual_steal} points, and {friend.name} loses {actual_steal} points!")
                    player_for_reaction = friend
                #Need to implement the not negative number logic
                self.gameBoard.append_agent_points(player.name, actual_steal)
                self.gameBoard.append_agent_points(friend.name, -actual_steal)
                
            
            self.gameBoard.host_broadcast(result_host_string)
            reaction = player_for_reaction.respond_to(self.gameBoard, result_host_string)
            self.publicPrivateResponse(player_for_reaction, reaction)
            
        