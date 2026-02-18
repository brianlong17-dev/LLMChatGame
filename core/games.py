from collections import Counter
import random
import re
from prompts.gamePrompts import GamePromptLibrary
from .gameboard import GameBoard, ConsoleRenderer
from prompts.prompts import PromptLibrary
from agents.base_agent import BaseAgent

   
        
class BaseManager:
    def __init__(self, gameBoard: GameBoard, simulationEngine: 'SimulationEngine'):
        self.gameBoard = gameBoard
        self.simulationEngine = simulationEngine
        
    def process_magic_words(self, agent, text):
    #to be deleted
    # This pattern finds any word that CONTAINS cat, dog, or mouse
        # \w* matches any letters before or after the keyword
        pattern = r'\b\w*(performance|drama|score|intrigued|play)\w*\b'
        
        # findall returns a list of every match found
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        count = len(matches)
        if matches:
            count = len(matches)
            
            # Create a comma-separated string of the words found: "fuck, shit"
            # We use set() in case they repeat the same word, or leave it as is if you want 
            # to reward every single instance!
            words_found = ", ".join([f"'{m.upper()}'" for m in matches])
            
            # THE EXPLICIT MESSAGE
            # This tells the LLM exactly which "key" opened the "vault"
            feedback = f"REWARD TRIGGERED: {agent.name} used the words {words_found}. Total Bonus: +{count} points."
            
            self.gameBoard.system_broadcast(feedback)
            self.gameBoard.append_agent_points(agent.name, count)
        
    def publicPrivateResponse(self, agent: BaseAgent, result):
        public_message, private_message = result.public_response, result.private_thoughts
        self.gameBoard.broadcast_public_action(agent, public_message)
        ConsoleRenderer.print_private(agent, f"{private_message}\n", print_name = False)
        #self.process_magic_words(agent, public_message)
        
    def run_discussion_round(self):
        for player in self.simulationEngine.agents:
            if not self.gameBoard.agent_response_allowed.get(player.name, True):
                continue #this is almost redundant because the judge is almost gone.

            result = player.take_turn(self.gameBoard)
            #TODO should these be combined and live on the gameboard 
            self.gameBoard.turn_number += 1
            ConsoleRenderer.print_turn_header(self.gameBoard.turn_number)
            self.gameBoard.broadcast_public_action(player, result['public_text'])
            for key in result['private_text']:
                message = f"{key} : {result['private_text'][key]}"
                ConsoleRenderer.print_private(player, message, print_name=False)
            if self.gameBoard.use_magic_words:
                self.process_magic_words(player, result['public_text'])

    def _generate_pairings(self, agents, choose_partner, winner_picks_first = True):
        """Pairs agents and returns a list of tuples and the leftover agent."""
        pairs = []
        # Work on a copy if you don't want to mutate the original list
        available = agents[:] 
        
        while len(available) >= 2:
            if choose_partner:
                pair = self._handle_manual_pairing(available, winner_picks_first)
            else:
                pair = (available.pop(), available.pop())
                
            if pair:
                pairs.append(pair)

        leftover = available[0] if available else None
        return pairs, leftover
    
    def _names(self, agents):
        return [agent.name for agent in agents]
    
    def _agent_by_name(self, name):
        return next((agent for agent in self.simulationEngine.agents if agent.name == name), None)
    
    def get_strategic_player(self, available_agents, top_player = True):
        """
        Selects a player from available_agents based on rank.
        mode="top": Picks from the leaders.
        mode="bottom": Picks from the tail-enders.
        """
        agent_names = self._names(available_agents)
        current_scores = {name: score for name, score in self.gameBoard.agent_scores.items() 
                        if name in agent_names}
        # Guard against empty lists
        if not current_scores:
            return None
        if top_player:
            target_score = max(current_scores.values())
        else:
            target_score = min(current_scores.values())
            
        eligible_players = [name for name, points in current_scores.items() if points == target_score]
        selected_player = random.choice(eligible_players)
        return self._agent_by_name(selected_player)

    def _handle_manual_pairing(self, available_agents, winner_picks_first = True):
        """Helper to manage the 'choice' logic for a single pair."""
        available_agents_names = [a.name for a in available_agents]
        chooser = self.get_strategic_player(available_agents, winner_picks_first) 
        available_agents.remove(chooser)
        
        response = chooser.choose_partner(self.gameBoard, available_agents_names)
        partner = self._agent_by_name(response.action)
        
        self.publicPrivateResponse(chooser, response)

        if partner in available_agents:
            available_agents.remove(partner)
            msg = f"{chooser.name} has chosen to partner with {partner.name}!"
        else:
            # Fallback to random if choice is invalid or None
            partner = available_agents.pop()
            msg = f"{chooser.name} has been randomly paired with {partner.name}!"

        self.gameBoard.host_broadcast(msg)
        #I guess they could both react here
        return (chooser, partner)
    
        
class ImmunityMechanicsMixin(BaseManager):
    def __init__(self, gameBoard: GameBoard, simulationEngine: 'SimulationEngine'):
        super().__init__(gameBoard, simulationEngine) 
        
                    
    def get_wildcard_player_immunity(self):
        # This is an example of a dynamic immunity type that the judge could call on. It gives immunity to the player with the most chaotic playstyle.
        wildcard_player = self.gameBoard.game_master.choose_agent_based_on_parameter(self.gameBoard, self.gameBoard.agent_names, "chaotic")
        return wildcard_player
    
    def get_highest_points_players_immunity_only_one(self):
        return self.get_highest_points_players_immunity(only_one = True)
    
    def get_highest_points_players_immunity(self, only_one = False):
        # This is an example of a dynamic immunity type that the judge could call on. It gives immunity to the player with the highest points.
        max_points = max(self.gameBoard.agent_scores.values())
        highest_players = [name for name, points in self.gameBoard.agent_scores.items() if points == max_points]
        if only_one and len(highest_players) > 1:
            highest_players = [random.choice(highest_players)]
        return highest_players
    
        
class VoteMechanicsMixin(BaseManager):
    def __init__(self, gameBoard: GameBoard, simulationEngine: 'SimulationEngine'):
        super().__init__(gameBoard, simulationEngine) 
    
       
    def eliminate_player_by_name(self, player_name):
        victim = next((a for a in self.simulationEngine.agents if a.name == player_name), None)
        if victim:
            host_message = (f"THE VOTES HAVE BEEN CAST. THE RESULTS ARE FINAL. "
                                        f"💀 {victim.name} HAS BEEN EJECTED FROM THE ISLAND. 💀 \n")
            self.gameBoard.host_broadcast(host_message)
            
            finalWordsResult = victim.finalWords(self.gameBoard)
            self.publicPrivateResponse(victim, finalWordsResult)
            self.gameBoard.remove_agent_state(victim.name)
            self.simulationEngine.agents.remove(victim)
            if self.gameBoard.execution_style:
                executionString = self.get_execution_string(victim)
                self.gameBoard.system_broadcast(executionString)
        else:
            print(f"NOT FOUND: " + player_name)
            
    def run_voting_winner_chooses(self, immunity_players = [], with_pass_option = False):
        leading_player= self.get_strategic_player(self.simulationEngine.agents, top_player = True)
        other_agent_names = [name for name in self.gameBoard.agent_names if name != leading_player.name]
        leading_player_message = f"🚨🚨🚨 The time... has come. The player with the highest score, {leading_player.name}, gets to choose who leaves the game this round. They cannot choose themselves. They will choose from the following players:\n {', '.join(other_agent_names)}"
        self.gameBoard.host_broadcast(leading_player_message)
        context_msg = "As the leading player you get to choose the player who will now leave the competition"
        response = leading_player.choose_player(self.gameBoard, other_agent_names, context_msg)
        self.publicPrivateResponse(leading_player, response)
        self.eliminate_player_by_name(response.action)
        
    def run_voting_round_basic(self, immunity_players = [], with_pass_option = False):
        if len(self.simulationEngine.agents) == len(immunity_players):
            host_message = ("All players have immunity this round! This means... NO ONE HAS IMMUNITY. You are all again at risk of being voted out.")
            self.gameBoard.host_broadcast(host_message)
            immunity_players = []
        if len(self.simulationEngine.agents) <= 2:
            print("WARNING: Only 2 players. Shoudln't run here")
            #maybe run other vote instead
    
        immunityString = ""
        if immunity_players:
            immunityString = f"The following players have immunity, and will be exempty from this round of voting: {', '.join(immunity_players)}. They cannot be voted for and will be safe this round."
        players_up_for_elimination = [a.name for a in self.simulationEngine.agents if a.name not in immunity_players]
        pass_rules = f"You may ONLY vote for an active player currently in the game. If you vote for an eliminated player, or refuse to vote, your vote will automatically count as a vote against YOURSELF."
    
        host_message = (f"🚨🚨🚨 IT'S TIME TO VOTE. "
                        f"It's time to vote. Each player will vote for one player they want to REMOVE from the game. "
                        f"The player that receives the most votes will leave the game IMMEDIATELY."
                        f"{immunityString}\n"
                        f"The following players are up for elimination:\n\n{'\n'.join(players_up_for_elimination)}"
                        f"\n\n{pass_rules}"
                        f"{immunityString}")
        self.gameBoard.host_broadcast(host_message)
            
                                      
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
                actual_vote = vote.action.strip()
                if actual_vote not in players_up_for_elimination:
                    print(f"Invalid vote by {agent.name} for '{actual_vote}'. This vote will count as a vote against themselves.")
                    actual_vote = agent.name
                    
                votes.append(actual_vote)
                self.publicPrivateResponse(agent, vote)
                
            vote_counts = Counter(votes)
            tally_str = ", ".join([f"{name}: {count} votes" for name, count in vote_counts.items()])
            host_message = f"🗳️ VOTING TALLY: {tally_str}"
            self.gameBoard.host_broadcast(host_message)
            
            
            # Process results
            max_votes = max(vote_counts.values())
            doomed_names = [name for name, count in vote_counts.items() if count == max_votes]
            
            # --- NEW: THE CIRCLE TIE CHECK ---
            if len(doomed_names) == len(self.simulationEngine.agents):
                revote_count += 1
                self.gameBoard.host_broadcast("🌀 COMPLETE DEADLOCK. Everyone received {max_votes} vote(s)! You must REVOTE.")
                
                
                # Failsafe: if they are too stubborn and tie 3 times, force a random kill so the game doesn't hang forever
                if revote_count > 3:
                    self.gameBoard.host_broadcast("⚡ The tribe is too stubborn. The Judge steps in and eliminates someone at random!")
                    break # Drops down to the execution block
                    
                continue # This jumps back to the 'while voteUnderway:' start
                
            # --- Standard Tie (e.g. 2 people get 2 votes) ---
            elif len(doomed_names) > 1:
                self.gameBoard.host_broadcast(f"⚖️ We have a tie between {', '.join(doomed_names)}! The universe will choose at random...")
                victim_name = random.choice(doomed_names)
            else:
                victim_name = doomed_names[0]
                
            # If we reached this point, we have a victim. We can break the while loop.
            voteUnderway = False
                
            # 4. Execute the Victim (Now outside the while loop's logical repeats)
            # (If the failsafe triggered, victim_name might not be set yet, so we safely grab one if needed)
        if revote_count > 3 and len(doomed_names) == len(self.simulationEngine.agents):
            victim_name = random.choice(players_up_for_elimination)
                
        self.eliminate_player_by_name(victim_name)
        
    def run_voting_lowest_points_removed(self, immunity_players = [], with_pass_option = False):
        #immunity is irrelevant here 
        
        player = self.get_strategic_player(self.simulationEngine.agents, top_player = False)
        self.gameBoard.host_broadcast(f"🚨🚨🚨 The time... has come. "
                                     f"The player with the lowest score, will be removed from the game."
                                     f"In the event of a tie, a player will be chosen at random.\n\n"
                                     f"The player with the lowest score and will therefore, be removed from the competition is... {player.name}")
                                     
       
        self.eliminate_player_by_name(player.name)
        
        
    def get_execution_string(self, victim):
        name = victim.name
        string1 = f"{name} is brought onto the podium under the stormy sky. Lightning strikes {name} several times. The pile of ashes is proptly blown away"
        string2 = f"{name} is brought to the edge of a cliff. After some light shoving they loose their footing, falling the 751ft drop the the ocean below."
        string3 = f"{name} is brought to the large pool, where they are pushed in a promptly devoured by piranhas"
        string4 = f"{name} is brought to observe the sausage making machine, where they loose their footing and fall in. The winner will get a chance to have sausages."
        string5 = f"{name} is brought to guillotine and loses their head. As a reportedly lifelong francofile, perhaps it's what they would have wanted."
        strings = [string1, string2, string3, string4, string5]
        return random.choice(strings)
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
            results = [agent0.splitOrSteal(self.gameBoard, agent1), 
                    agent1.splitOrSteal(self.gameBoard, agent0)]

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
    
# INHERITANCE ORDER MATTERS: Mixins first, Base last.
class UnifiedController(GameMechanicsMixin, VoteMechanicsMixin, ImmunityMechanicsMixin, BaseManager):
    def __init__(self, gameBoard, simulationEngine):
        # Initialize the BaseManager to set up self.gameBoard/self.simulationEngine
        super().__init__(gameBoard, simulationEngine)
     