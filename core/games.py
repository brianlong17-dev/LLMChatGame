from collections import Counter
import random

from .gameboard import GameBoard, ConsoleRenderer
from prompts.prompts import PromptLibrary


class VoteAndGameManager:
    
    
    def __init__(self, gameBoard: GameBoard, simulationEngine: 'SimulationEngine'):
        self.gameBoard = gameBoard
        self.simulationEngine = simulationEngine
        
    def broadcast_public_action(self, player_name: str, message: str, color: str = "RESET"):
        """
        The SINGLE source of truth for public events. 
        Guarantees that if it is seen, it is remembered.
        """
        # 1. Update the Model (History)
        self.gameBoard._update_history(player_name, message)
        
        # 2. Update the View (Terminal UI)
        ConsoleRenderer.print_public_action(player_name, message, color)
    
    def run_discussion_round(self):
        for player in self.simulationEngine.players():
            if player.isAgent() and not self.gameBoard.agent_response_allowed.get(player.name, True):
                continue #this is almost redundant because the judge is almost gone.

            result = player.take_turn(self.gameBoard)
            #TODO should these be combined and live on the gameboard 
            self.gameBoard.turn_number += 1
            ConsoleRenderer.print_turn_header(self.gameBoard.turn_number)
            self.broadcast_public_action(player.name, result['public_text'], color=player.color)
            for key in result['private_text']:
                ConsoleRenderer.print_private_thought(thought_type = key, message=result['private_text'][key], color_name=player.color)
                
    def get_wildcard_player_immunity(self):
        # This is an example of a dynamic immunity type that the judge could call on. It gives immunity to the player with the most chaotic playstyle.
        wildcard_player = self.gameBoard.game_master.choose_agent_based_on_parameter(self.gameBoard, self.gameBoard.agent_names, "chaotic")
        return wildcard_player
    def get_highest_points_players_immunity(self):
        # This is an example of a dynamic immunity type that the judge could call on. It gives immunity to the player with the highest points.
        max_points = max(self.gameBoard.agent_scores.values())
        highest_players = [name for name, points in self.gameBoard.agent_scores.items() if points == max_points]
        return highest_players
    
    def run_game_prisoners_dilemma(self):
        
        splitPoints = PromptLibrary.pd_split
        stealPoints = PromptLibrary.pd_steal
        bothSteal = PromptLibrary.pd_both_steal
        
        # 1. Broadcast the rules
        intro_message = (f"It's time to play a game to build points. "
                        f"It's time to find out who your real friends are. Who to trust, and who to play. "
                        f"The game: Prisoner's Dilemma.\n"
                        f"Each player will be paired with another player. In each pairing you get a choice: SPLIT or STEAL.\n"
                        f"- If both players decide to SPLIT, they will receive {splitPoints} points each.\n"
                        f"- If one player decides to STEAL while the other splits, the stealer receives {stealPoints} points, and the victim gets 0.\n"
                        f"- If both choose to STEAL, they will receive {bothSteal} point each. \n\n")
        self.broadcast_public_action("SYSTEM", intro_message)

        # 2. Pairing Logic
        # Assuming self.simulationEngine.agents is a list of your agent objects. We shuffle to make pairings random.
        available_agents = list(self.simulationEngine.agents)
        random.shuffle(available_agents)
        
        pairs = []
        while len(available_agents) >= 2:
            pairs.append((available_agents.pop(), available_agents.pop()))
            
        # Handle the leftover player if there is an odd number of agents
        if available_agents:
            leftover_agent = available_agents[0]
            self.broadcast_public_action("SYSTEM", f"{leftover_agent.name} is the odd one out this round! They get to sit back and automatically receive {splitPoints} points\n\n")
            self.gameBoard.append_agent_points(leftover_agent.name, splitPoints)

        # 3. Execute the pairings
        for agent0, agent1 in pairs:
            self.broadcast_public_action("SYSTEM", f"{agent0.name} vs {agent1.name}. Do you choose to split, or steal?\n")
            # --- BLIND VOTING ---
            # Get both decisions BEFORE saving to the shared gameBoard.
            # This prevents Agent 1 from reading Agent 0's decision in the context window.
            result0 = agent0.splitOrSteal(self.gameBoard, agent1)
            result1 = agent1.splitOrSteal(self.gameBoard, agent0)
            
            # Now that both have decided, reveal their public responses and log private thoughts
            self.broadcast_public_action(agent0.name, result0.public_response)
            ConsoleRenderer.print_private_thought(result0.private_thoughts, color_name=agent0.color)
            
            self.broadcast_public_action(agent1.name, result1.public_response)
            ConsoleRenderer.print_private_thought(result1.private_thoughts, color_name=agent1.color)
            
            # Clean the choices to ensure easy matching (assuming Instructor/Pydantic returns a string here)
            choice0 = result0.action.strip().lower()
            choice1 = result1.action.strip().lower()
            
            # --- RESOLVE OUTCOMES ---
            result_system_message = ""
            
            if choice0 == 'split' and choice1 == 'split':
                result_system_message = (f"Congratulations {agent0.name} and {agent1.name}. "
                                        f"You both decided to SPLIT. You each receive {splitPoints} points.")
                self.gameBoard.append_agent_points(agent0.name, splitPoints)
                self.gameBoard.append_agent_points(agent1.name, splitPoints)
                
            elif choice0 == 'steal' and choice1 == 'steal':
                result_system_message = (f"OH NO {agent0.name} and {agent1.name}.... "
                                        f"You both decided to STEAL. You each receive {bothSteal} point.")
                self.gameBoard.append_agent_points(agent0.name, bothSteal)
                self.gameBoard.append_agent_points(agent1.name, bothSteal)
                
            else:
                # One splits, one steals
                if choice0 == 'steal':
                    stealing_agent, victim_agent = agent0, agent1
                else:
                    stealing_agent, victim_agent = agent1, agent0
                    
                result_system_message = (f"OH NO! {stealing_agent.name} decided to STEAL from {victim_agent.name}! "
                                        f"{stealing_agent.name} gets {stealPoints} points, while {victim_agent.name} gets nothing.")
                self.gameBoard.append_agent_points(stealing_agent.name, stealPoints)
                
            # Broadcast the result of the pairing
            self.broadcast_public_action("SYSTEM", f"\n{result_system_message}\n")
            
            # --- GATHER REACTIONS ---
            # Let both agents react to the betrayal or cooperation
            for agent in (agent0, agent1):
                reaction = agent.respond_to(self.gameBoard, result_system_message)
                self.broadcast_public_action(agent.name, f"{reaction.public_response}", color=agent.color)
                ConsoleRenderer.print_private_thought(reaction.private_thoughts, speaker_name=agent.name, color_name=agent.color)
                

    def eliminate_player(self, player_name):
        victim = next((a for a in self.simulationEngine.agents if a.name == player_name), None)
        if victim:
            self.broadcast_public_action("SYSTEM", f"THE VOTES HAVE BEEN CAST. THE RESULTS ARE FINAL. "
                                        f"💀 {victim.name} HAS BEEN VOTED OFF THE ISLAND. 💀 \n")
            finalWordsResult = victim.finalWords(self.gameBoard)
            ConsoleRenderer.print_private_thought(speaker_name=victim.name, thought_type="Final Thoughts", message=f"{finalWordsResult.private_thoughts}\n", color_name=victim.color)
            self.broadcast_public_action(victim.name, f"{finalWordsResult.public_response}\n", color=victim.color)
            self.gameBoard.remove_agent_state(victim.name)
            self.simulationEngine.agents.remove(victim)
            
    def run_voting_round_basic(self, immunity_players = [], with_pass_option = False):
        if len(self.simulationEngine.agents) == immunity_players:
            self.broadcast_public_action("SYSTEM", f"All players have immunity this round! This means... NO ONE HAS IMMUNITY. You are all again at risk of being voted out.")
            immunity_players = []
        if len(self.simulationEngine.agents) <= 2:
            print("WARNING: Only 2 players. Shoudln't run here")
            #maybe run other vote instead
    
        immunityString = ""
        if immunity_players:
            immunityString = f"The following players have immunity, and will be exempty from this round of voting: {', '.join(immunity_players)}. They cannot be voted for and will be safe this round."
        players_up_for_elimination = [a.name for a in self.simulationEngine.agents if a.name not in immunity_players]
        pass_rules = f"You may ONLY vote for an active player currently in the game. If you vote for an eliminated player, or refuse to vote, your vote will automatically count as a vote against YOURSELF."
    
        self.broadcast_public_action("SYSTEM", f"🚨🚨🚨 IT'S TIME TO VOTE. "
                                    f"It's time to vote. Each player will vote for one player they want to REMOVE from the game. "
                                    f"The player that receives the most votes will leave the game IMMEDIATELY."
                                    f"{immunityString}\n"
                                    f"The following players are up for elimination:\n {'\n'.join(players_up_for_elimination)}"
                                    f"\n{pass_rules}")
                                    
        voteUnderway = True
        revote_count = 0 # Optional failsafe to prevent infinite loops!
        
        while voteUnderway:
            # We initialize these INSIDE the loop so they reset on a revote
            votingResults = []
            votes = []
            
            # Collect votes
            for agent in self.simulationEngine.agents:
                votingResults.append(agent.voteOnePlayerOff(self.gameBoard, players_up_for_elimination))
                
            for agent, vote in zip(self.simulationEngine.agents, votingResults):
                votes.append(vote.action) 
                self.broadcast_public_action(agent.name, vote.public_response, color=agent.color)
                ConsoleRenderer.print_private_thought(agent.name, f"{vote.private_thoughts} \n", color_name=agent.color)
                
            vote_counts = Counter(votes)
            tally_str = ", ".join([f"{name}: {count} votes" for name, count in vote_counts.items()])
            self.broadcast_public_action("SYSTEM", f"🗳️ VOTING TALLY: {tally_str}")
            
            # Process results
            max_votes = max(vote_counts.values())
            doomed_names = [name for name, count in vote_counts.items() if count == max_votes]
            
            # --- NEW: THE CIRCLE TIE CHECK ---
            if len(doomed_names) == len(self.simulationEngine.agents):
                revote_count += 1
                self.broadcast_public_action("SYSTEM", f"🌀 COMPLETE DEADLOCK. Everyone received {max_votes} vote(s)! You must REVOTE.")
                
                # Failsafe: if they are too stubborn and tie 3 times, force a random kill so the game doesn't hang forever
                if revote_count > 3:
                    self.broadcast_public_action("SYSTEM", "⚡ The tribe is too stubborn. The Judge steps in and eliminates someone at random!")
                    break # Drops down to the execution block
                    
                continue # This jumps back to the 'while voteUnderway:' start
                
            # --- Standard Tie (e.g. 2 people get 2 votes) ---
            elif len(doomed_names) > 1:
                self.broadcast_public_action("SYSTEM", f"⚖️ We have a tie between {', '.join(doomed_names)}! The universe will choose at random...")
                victim_name = random.choice(doomed_names)
            else:
                victim_name = doomed_names[0]
                
            # If we reached this point, we have a victim. We can break the while loop.
            voteUnderway = False
                
            # 4. Execute the Victim (Now outside the while loop's logical repeats)
            # (If the failsafe triggered, victim_name might not be set yet, so we safely grab one if needed)
        if revote_count > 3 and len(doomed_names) == len(self.simulationEngine.agents):
            victim_name = random.choice(self.simulationEngine.agents).name
                
        self.eliminate_player(victim_name)