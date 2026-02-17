# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "instructor",
#     "google-genai",
#     "python-dotenv",
#     "pydantic",
# ]
# ///

import os
import random
import instructor
from collections import Counter, deque
from datetime import datetime
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents.characterGeneration import CharacterGenerator
from core.game_configs import *
from core.games import VoteAndGameManager
from prompts.prompts import PromptLibrary
from agents.actors import *
from agents.player import Debater
from agents.gameMaster import GameMaster
from agents.judge import Judge
from models.player_models import *
from .gameboard import GameBoard


class PhaseRecipe(BaseModel):
    pre_game_discussion_rounds: int = 2
    mini_game: Optional[GameDefinition] = None
    pre_vote_discussion_rounds: int = 1
    vote_type: Optional[VoteDefinition] = None
    post_vote_discussion_rounds: int = 0
    immunity_types: Optional[List[ImmunityDefinition]] = None  # e.g., ["winner_immunity", "public_vote_immunity"]
    
    def messageString(self, phase_number):
        game_description = ""
        vote_description = ""
        pre_game_discussion_message = ""
        pre_vote_discussion_message = ""
        immunity_message = ""
        
        if self.pre_game_discussion_rounds > 0:
            if self.mini_game:
                pre_game_discussion_message = f"Before we start the mini game, we will have {self.pre_game_discussion_rounds} rounds of discussion to strategize and form alliances.\n"
            else:
                pre_game_discussion_message = f"We will start with {self.pre_game_discussion_rounds} rounds of discussion to strategize and form alliances.\n"
                
        if self.mini_game:
            game_description += f"We will be playing a mini game this phase: {self.mini_game.display_name}. {self.mini_game.rules_description}\n"
        
        if self.pre_vote_discussion_rounds > 0:
            pre_vote_discussion_message = f"We will have {self.pre_vote_discussion_rounds} rounds of discussion before the voting round to discuss and plan.\n"
            
        if self.immunity_types:
            immunity_message += "HOWEVER! This voting round phase has the following immunities in play:\n"
            for immunity in self.immunity_types:
                immunity_message += f"- {immunity.display_name}: {immunity.rules_description}\n"
        if self.vote_type:
            vote_description += f"We will be playing a voting game this phase: {self.vote_type.display_name}. {self.vote_type.rules_description}\n"
            
        
        
        message = f"🚨 WELCOME PLAYERS, TO PHASE {phase_number} 🚨\n"
        message += pre_game_discussion_message
        message += game_description
        message += pre_vote_discussion_message
        message += vote_description
        return message
        
    
    
class SimulationEngine:
    def __init__(self, model_name: str = "gemini-2.0-flash-lite", number_of_players = 5):
        load_dotenv()
        self.client = instructor.from_provider('google/' + model_name, api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name
        self.game_master = GameMaster(self.client, model_name)
        self.generator = CharacterGenerator(self.client, self.model_name)
        self.judge = Judge("Judge", "You are a reality tv producer, seeking to create the most compelling drama.", "A curious individual", self.client, model_name)
        self.finalPhase = False
        self.roundsRemaining = None 
        self.rounds_per_phase = 3
        self.phase_number = 0
        self.gameBoard = GameBoard(self.game_master)
        self.game_manager = VoteAndGameManager(self.gameBoard, self)
        
    def initialiseGameBoard(self):
        self.gameBoard.initialize_agents(self.agents)
        
        
    def players(self):
        if len(self.agents) <= 2:
            return self.agents #+ [self.judge] 
        return self.agents #+ [self.judge] 
    
    def get_phase_recipe(self):
        recipe1 = PhaseRecipe(
            pre_game_discussion_rounds=2,
            mini_game=PRISONERS_DILEMMA,
            pre_vote_discussion_rounds=1,
            vote_type=EACH_PLAYER_VOTES_TO_REMOVE,
            post_vote_discussion_rounds=0,
            immunity_types=[HIGHEST_POINT_IMMUNITY] #"HighestPointPlayerImmunity(), WildcardImmunity()]
        )
        
        recipe2 = PhaseRecipe(
            pre_game_discussion_rounds=0,
            mini_game=None,
            pre_vote_discussion_rounds=2,
            vote_type=EACH_PLAYER_VOTES_TO_REMOVE,
            post_vote_discussion_rounds=0
        )
        if self.phase_number < 5:
            return recipe1
        else:
            return recipe2
        
    def runPhase(self, recipe: PhaseRecipe):
        
        intro = recipe.messageString(self.phase_number)
        self.gameBoard.print_and_save("SYSTEM", intro)
        
        for _ in range(recipe.pre_game_discussion_rounds):  
            self.gameBoard.newRound()
            self.game_manager.run_discussion_round()
        
        if recipe.mini_game:
            self.gameBoard.newRound()
            #this printing has to be moved.
            self.gameBoard.print_and_save("SYSTEM", f"\n🎲 TRIGGERING EVENT: {recipe.mini_game.display_name}")
            self.gameBoard.print_and_save("SYSTEM", recipe.mini_game.rules_description)
            recipe.mini_game.execute_game(self.game_manager)
        
        for _ in range(recipe.pre_vote_discussion_rounds):
            self.gameBoard.newRound()
            self.game_manager.run_discussion_round()
        
        if recipe.vote_type:
            
            self.gameBoard.newRound()
            if recipe.vote_type:
                immune_players = [] # Use a standard list!
                
                if recipe.immunity_types:
                    for immunity in recipe.immunity_types:
                        result = immunity.execute_game(self.game_manager)
                        if isinstance(result, list):
                            immune_players.extend(result)
                        else:
                            immune_players.append(result)
            self.gameBoard.print_and_save("SYSTEM", f"\n🗳️ TRIGGERING VOTE: {recipe.vote_type.display_name}")
            self.gameBoard.print_and_save("SYSTEM", recipe.vote_type.rules_description)
            
            recipe.vote_type.execute_game(self.game_manager, immunity_players=immune_players)
        
        for _ in range(recipe.post_vote_discussion_rounds):
            self.gameBoard.newRound()
            self.game_manager.run_discussion_round()
                
        return
        phase1 = (2, gameName, 1, voteType)
        genericPhase = (2, None, 0, voteType)
        # Run for rounds_per_phase rounds
        
        
        for _ in range(self.rounds_per_phase):
            if self.finalPhase:
                self.gameBoard.print_and_save("SYSTEM", f"🚨🚨🚨{self.roundsRemaining} ROUNDS REMAIN UNTIL THE FINAL VOTE. THE PLAYER WITH THE MOST POINTS FROM THE JUDGE WILL GET THE DECIDING VOTE ")
                self.roundsRemaining -= 1
            self.gameBoard.newRound()
            
            for player in self.players():
                if player.isAgent() and not self.gameBoard.agent_response_allowed.get(player.name, True):
                    continue
                
                #result =self.gameBoard.process_turn(player)
                if (creation_turn := result.get("creation_turn")) is not None:
                    self.handle_agent_creation(creation_turn)
            
            self.gameBoard.print_leaderboard()

        # --- THE VOTING PHASE ---
        self.execute_end_of_phase()
            
            
            
  
    def set_up_players(self, number_of_players, generic_players):
        if generic_players:
            self.agents = self.generator.genericPlayers(number_of_players)
        else:
            self.agents = [self.generator.generate_random_debater() for _ in range(number_of_players)]
        
         
    def run(self, topic: str, rounds_per_discussion_phase=1, number_of_players = 2, generic_players=False):
        print(f"\n🚀 Simulation Started: {topic}\n" + "="*50)
        self.rounds_per_phase = rounds_per_discussion_phase
        self.set_up_players(number_of_players, generic_players)
        self.initialiseGameBoard()
        
        
        self.gameBoard.print_and_save("System", f"Goal: {topic}")
        while len(self.agents) > 1:
            self.phase_number += 1
            self.runPhase(self.get_phase_recipe())
            
        print(f"🏆 FINAL SURVIVOR: {self.agents[0].name}")
        
    def execute_prisoners_dilema_game(self):
        splitPoints = PromptLibrary.pd_split
        stealPoints = PromptLibrary.pd_steal
        bothSteal = PromptLibrary.pd_both_steal
        
        # 1. Broadcast the rules
        intro_message = (f"🚨🚨🚨 {self.rounds_per_phase} ROUNDS COMPLETE. "
                        f"It's time to play a game to build points. "
                        f"It's time to find out who your real friends are. Who to trust, and who to play. "
                        f"The game: Prisoner's Dilemma.\n"
                        f"Each player will be paired with another player. In each pairing you get a choice: SPLIT or STEAL.\n"
                        f"- If both players decide to SPLIT, they will receive {splitPoints} points each.\n"
                        f"- If one player decides to STEAL while the other splits, the stealer receives {stealPoints} points, and the victim gets 0.\n"
                        f"- If both choose to STEAL, they will receive {bothSteal} point each.")
        self.gameBoard.print_and_save("SYSTEM", intro_message)

        # 2. Pairing Logic
        # Assuming self.agents is a list of your agent objects. We shuffle to make pairings random.
        available_agents = list(self.agents)
        random.shuffle(available_agents)
        
        pairs = []
        while len(available_agents) >= 2:
            pairs.append((available_agents.pop(), available_agents.pop()))
            
        # Handle the leftover player if there is an odd number of agents
        if available_agents:
            leftover_agent = available_agents[0]
            self.gameBoard.print_and_save("SYSTEM", f"{leftover_agent.name} is the odd one out this round! They get to sit back and automatically receive {splitPoints} points.")
            self.gameBoard.append_agent_points(leftover_agent.name, splitPoints)

        # 3. Execute the pairings
        for agent0, agent1 in pairs:
            
            # --- BLIND VOTING ---
            # Get both decisions BEFORE saving to the shared gameBoard.
            # This prevents Agent 1 from reading Agent 0's decision in the context window.
            result0 = agent0.splitOrSteal(self.gameBoard, agent1)
            result1 = agent1.splitOrSteal(self.gameBoard, agent0)
            
            # Now that both have decided, reveal their public responses and log private thoughts
            self.gameBoard.print_and_save(agent0.name, result0.public_response)
            self.gameBoard._print(agent0.name, f"[Thoughts]: {result0.private_thoughts}\n", is_private=True)
            
            self.gameBoard.print_and_save(agent1.name, result1.public_response)
            self.gameBoard._print(agent1.name, f"[Thoughts]: {result1.private_thoughts}\n", is_private=True)
            
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
            self.gameBoard.print_and_save("SYSTEM", result_system_message)
            
            # --- GATHER REACTIONS ---
            # Let both agents react to the betrayal or cooperation
            for agent in (agent0, agent1):
                reaction = agent.respond_to(self.gameBoard, result_system_message)
                self.gameBoard.print_and_save(agent.name, f"{reaction.public_response}\n")
                
                # Use getattr as a fallback in case your Pydantic model uses 'thought_process' instead of 'private_thoughts'
                self.gameBoard._print(agent.name, f"[Thoughts]: {reaction.private_thoughts}\n", is_private=True)         
                
                
        
    def initiateFinalPhase(self):
        self.finalPhase = True
        #self.rounds_per_phase = self.rounds_per_phase * 3
        self.roundsRemaining = self.rounds_per_phase
        systemMessage = (f"SYSTEM ALERT: THE GAME HAS CHANGED. You are in the Final Two. Your previous rivalries do not matter. The ONLY way to win is to directly answer the Judge's prompts. If you ignore the Judge to attack your opponent, you will lose points."
        f"If you earn 15 Points from the Judge, you unlock a targeted Assassination. You can spend your 15 points to immediately eliminate any player from the game, bypassing the voting phase entirely. To do this, add [ASSASSINATE: Player Name] to the end of your response.")
        self.gameBoard.print_and_save("System", systemMessage)
    
           
    def execute_voting_phase_each_votes(self):
        # 1. Early exit if only 2 players remain
        if len(self.agents) <= 2:
            self.execute_voting_phase() 
            return
            
        self.gameBoard.print_and_save("SYSTEM", f"🚨🚨🚨 {self.rounds_per_phase} ROUNDS COMPLETE. "
                                      f"It's time to vote. Each player will vote for one player they want to REMOVE from the game. "
                                      f"The player that receives the most votes will leave the game IMMEDIATELY."
                                      f"You may ONLY vote for an active player currently in the game. If you vote for an eliminated player, or refuse to vote, your vote will automatically count as a vote against YOURSELF.")
                                      
        voteUnderway = True
        revote_count = 0 # Optional failsafe to prevent infinite loops!
        
        while voteUnderway:
            # We initialize these INSIDE the loop so they reset on a revote
            votingResults = []
            votes = []
            
            # Collect votes
            for agent in self.agents:
                other_agent_names = [a.name for a in self.agents if a.name != agent.name]
                votingResults.append(agent.voteOnePlayerOff(self.gameBoard, other_agent_names))
                
            for agent, vote in zip(self.agents, votingResults):
                votes.append(vote.action) 
                
                self.gameBoard.print_and_save(agent.name, vote.public_response)
                self.gameBoard._print(agent.name, f"{vote.private_thoughts} \n", is_private=True)
                
            vote_counts = Counter(votes)
            tally_str = ", ".join([f"{name}: {count} votes" for name, count in vote_counts.items()])
            self.gameBoard.print_and_save("SYSTEM", f"🗳️ VOTING TALLY: {tally_str}")
            
            # Process results
            max_votes = max(vote_counts.values())
            doomed_names = [name for name, count in vote_counts.items() if count == max_votes]
            
            # --- NEW: THE CIRCLE TIE CHECK ---
            if len(doomed_names) == len(self.agents):
                revote_count += 1
                self.gameBoard.print_and_save("SYSTEM", f"🌀 COMPLETE DEADLOCK. Everyone received {max_votes} vote(s)! You must REVOTE.")
                
                # Failsafe: if they are too stubborn and tie 3 times, force a random kill so the game doesn't hang forever
                if revote_count > 3:
                    self.gameBoard.print_and_save("SYSTEM", "⚡ The tribe is too stubborn. The Judge steps in and eliminates someone at random!")
                    break # Drops down to the execution block
                    
                continue # This jumps back to the 'while voteUnderway:' start
                
            # --- Standard Tie (e.g. 2 people get 2 votes) ---
            elif len(doomed_names) > 1:
                self.gameBoard.print_and_save("SYSTEM", f"⚖️ We have a tie between {', '.join(doomed_names)}! The universe will choose at random...")
                victim_name = random.choice(doomed_names)
            else:
                victim_name = doomed_names[0]
                
            # If we reached this point, we have a victim. We can break the while loop.
            voteUnderway = False
            
        # 4. Execute the Victim (Now outside the while loop's logical repeats)
        # (If the failsafe triggered, victim_name might not be set yet, so we safely grab one if needed)
        if revote_count > 3 and len(doomed_names) == len(self.agents):
            victim_name = random.choice(self.agents).name
            
        victim = next((a for a in self.agents if a.name == victim_name), None)
        
        if victim:
            self.gameBoard.print_and_save("SYSTEM", f"THE VOTES HAVE BEEN CAST. THE RESULTS ARE FINAL. "
                                          f"💀 {victim.name} HAS BEEN VOTED OFF THE ISLAND. 💀 \n")
            finalWordsResult = victim.finalWords(self.gameBoard)
            self.gameBoard._print(victim.name, f"[Final Thoughts]: {finalWordsResult.private_thoughts}\n", is_private=True)
            self.gameBoard.print_and_save(victim.name, f"{finalWordsResult.public_response}\n")
            self.gameBoard.remove_agent_state(victim.name)
            self.agents.remove(victim)
        
        if len(self.agents) <= 2:
            self.initiateFinalPhase()
            
        #self.gameBoard.resetScores()     
            
    def execute_voting_phase(self):
        # 1. Identify the leader
        scores = self.gameBoard.agent_scores
        leader_name = max(scores, key=scores.get)
        leader = next(agent for agent in self.agents if agent.name == leader_name)
        
        leader_agent = next(a for a in self.agents if a.name == leader_name)
        
        other_agents = [a.name for a in self.agents if a.name != leader_name]
        
        self.gameBoard.print_and_save("SYSTEM", f"🚨 {self.rounds_per_phase} ROUNDS COMPLETE. {leader_name} has the most points and must vote someone off!")

        vote_result = leader.votePlayerOff(self.gameBoard)

        # 3. Process the execution
        victim_name = vote_result.action
        victim = next((a for a in self.agents if a.name == victim_name), None)
        
        if victim:
            self.gameBoard.print_and_save(leader_name, f"[{vote_result.private_thoughts}] I cast my vote. {vote_result.public_response}")
            self.gameBoard.print_and_save("SYSTEM", f"💀 {victim.name} HAS BEEN VOTED OFF THE ISLAND. 💀")
            finalWordsResult = victim.finalWords(self.gameBoard)
            self.gameBoard._print(victim.name, f"[Final Thoughts]: {finalWordsResult.private_thoughts}", is_private=True)
            self.gameBoard.print_and_save(victim.name, f"{finalWordsResult.public_response}")
            self.gameBoard.remove_agent_state(victim.name)
            self.agents.remove(victim)
            
        #reset scores
        for entry in self.gameBoard.agent_scores:
            self.gameBoard.agent_scores[entry] = 0
            
    def export_to_markdown(self, topic: str):
        folder = "output"
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"debate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\n")
            for entry in self.history:
                f.write(f"### {entry['speaker']}\n{entry['message']}\n\n")
        print(f"\n✅ Transcript saved to: {filename}")
        
    def handle_agent_creation(self, creation_turn):
        """Processes the Judge's request to manifest a new soul into the game."""
        if len(self.agents) > 10:
            self.gameBoard.print_and_save("SYSTEM", "The void is full. There are too many players to create someone new.")
            return

        # 1. Handle Unique Naming (e.g., 'Medusa' -> 'Medusa_2')
        base_name = creation_turn.name
        existing_count = sum(1 for a in self.agents if a.name.startswith(base_name))
        name = f"{base_name}{f'_{existing_count + 1}' if existing_count else ''}"
        
        # 2. Format the Private 'Creation' Text
        creation_private_text = (
            f"\n\033[1;33m[THE JUDGE (CREATING)]: I shall create... {name}.\033[0m\n"
            f"\033[3m(Concept: {creation_turn.private_thoughts})\033[0m\n"
            f"\033[3m(Form: {creation_turn.form})\033[0m\n"
            f"\033[3m(Persona: {creation_turn.persona})\033[0m"
        )
        
        # 3. Instantiate and Register the New Agent
        new_soul = Debater(
            name, 
            creation_turn.persona, 
            creation_turn.form, 
            self.client, 
            self.model_name
        )
        
        self.agents.append(new_soul)
        self.gameBoard.add_agent_state(name, new_soul.form)
        
        # 4. Broadcast to the Game
        self.gameBoard.print_and_save("SYSTEM", f"A new being appears: {name}")
        self.gameBoard._print("SYSTEM", creation_private_text, is_private=True)
    
   


