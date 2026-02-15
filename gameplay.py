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
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from characterGeneration import CharacterGenerator
from prompts import PromptLibrary
from actors import *
from models import *
from gameboard import GameBoard


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
        
    def initialiseGameBoard(self):
        self.gameBoard = GameBoard(self.game_master, [agent.name for agent in self.agents])
        for agent in self.agents:
            self.gameBoard.add_agent_state(agent.name, agent.form)
        for agent in self.agents:
            self.gameBoard.agent_forms[agent.name] = agent.form
        self.gameBoard.judge = self.judge
        
    def players(self):
        if len(self.agents) <= 2:
            return self.agents + [self.judge] 
        return self.agents #+ [self.judge] 
    
    def run(self, topic: str, rounds_per_phase=1, number_of_players = 2, generic_players=False):
        print(f"\n🚀 Simulation Started: {topic}\n" + "="*50)
        self.rounds_per_phase = rounds_per_phase
        if generic_players:
            self.agents = self.generator.genericPlayers()
        else:
            self.agents = [self.generator.generate_random_debater() for _ in range(number_of_players)]
        
        self.initialiseGameBoard()
        self.gameBoard.print_and_save("System", f"Goal: {topic}")
        
        while len(self.agents) > 1:
            # Run for rounds_per_phase rounds
            
            for _ in range(self.rounds_per_phase):
                if self.finalPhase:
                    self.gameBoard.print_and_save("SYSTEM", f"🚨🚨🚨{self.roundsRemaining} ROUNDS REMAIN UNTIL THE FINAL VOTE. THE PLAYER WITH THE MOST POINTS FROM THE JUDGE WILL GET THE DECIDING VOTE ")
                    self.roundsRemaining -= 1
                self.gameBoard.newRound()
                
                for player in self.players():
                    if player.isAgent() and not self.gameBoard.agent_response_allowed.get(player.name, True):
                        continue
                    
                    result =self.gameBoard.process_turn(player)
                    if (creation_turn := result.get("creation_turn")) is not None:
                        self.handle_agent_creation(creation_turn)
                
                self.gameBoard.print_leaderboard()

            # --- THE VOTING PHASE ---
            self.execute_voting_phase_each_votes()
            
        print(f"🏆 FINAL SURVIVOR: {self.agents[0].name}")
    
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
            f"\033[3m(Concept: {creation_turn.thought_process})\033[0m\n"
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
    
    
    def run2(self, topic: str, batch_size: int = 50, round_length = 5):
        print(f"\n🚀 Simulation Started: {topic}\n" + "="*50)
        self.gameBoard.print_and_save("System", f"Goal: {topic}")
        turn_count = 0
        keep_going = True
    
        while len(self.agents) > 1:
            self.gameBoard.newRound()
            print(self.gameBoard.agent_scores)
           
            # --- 2. AGENT TURNS ---
            for player in self.players():
                # Double check existence
                
                if player not in self.players(): continue
                if player.isAgent() and not self.gameBoard.agent_response_allowed.get(player.name, True):
                    self.gameBoard.print_and_save("SYSTEM", f"\n\033[1;30m[Skipped]\033[0m {player.name} is silenced by {PromptLibrary.judgeName}.")
                    continue
                turn_count += 1
                result = self.gameBoard.process_turn(player)
                
                if (creation_turn := result.get("creation_turn")) is not None:
                    self.handle_agent_creation(creation_turn)
                    
                
                    #do stuff
                if (target := result.get("ejection_target")) is not None:
                    
                    victim = next((a for a in self.agents if a.name.lower() in target.lower()), None)
                    
                    if victim:
                        message = (f"\n🚨 💀 JUDGMENT: {victim.name} HAS BEEN EXECUTED. 💀 🚨\n")
                        self.gameBoard.print_and_save("SYSTEM", message)
                        self.gameBoard.remove_agent_state(victim.name)
                        self.agents.remove(victim)
                
                
            
            self.gameBoard.print_leaderboard()

              
            
            if turn_count >= batch_size:
                    if input(f"\nBatch Complete. Continue? (y/n): ").strip().lower() != 'y':
                        keep_going = False
                    else:
                        batch_size += 20

            
        
        self.export_to_markdown(topic)

    def initiateFinalPhase(self):
        self.finalPhase = True
        self.rounds_per_phase = self.rounds_per_phase * 3
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
                votes.append(vote.name) 
                
                self.gameBoard.print_and_save(agent.name, vote.public_response)
                self.gameBoard._print(agent.name, f"{vote.thought_process} \n", is_private=True)
                
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
                                          f"💀 {victim.name} HAS BEEN VOTED OFF THE ISLAND. 💀")
            finalWordsResult = victim.finalWords(self.gameBoard)
            self.gameBoard._print(victim.name, f"[Final Thoughts]: {finalWordsResult.thought_process}", is_private=True)
            self.gameBoard.print_and_save(victim.name, f"{finalWordsResult.final_words}")
            self.gameBoard.remove_agent_state(victim.name)
            self.agents.remove(victim)
        
        if len(self.agents) <= 2:
            self.initiateFinalPhase()
            
        self.gameBoard.resetScores()     
            
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
        victim_name = vote_result.name
        victim = next((a for a in self.agents if a.name == victim_name), None)
        
        if victim:
            self.gameBoard.print_and_save(leader_name, f"[{vote_result.thought_process}] I cast my vote. {vote_result.public_response}")
            self.gameBoard.print_and_save("SYSTEM", f"💀 {victim.name} HAS BEEN VOTED OFF THE ISLAND. 💀")
            finalWordsResult = victim.finalWords(self.gameBoard)
            self.gameBoard._print(victim.name, f"[Final Thoughts]: {finalWordsResult.thought_process}", is_private=True)
            self.gameBoard.print_and_save(victim.name, f"{finalWordsResult.final_words}")
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
        
    

if __name__ == "__main__":
    engine = SimulationEngine()
    rounds = 2
    topicString = (f"At the end of {rounds} rounds, the  player with the most points votes off a player. THE GOAL IS THE BE THE LAST PLAYER STANDING!"
    )#f"In the final round, the player with the most points from the judge wins")
    engine.run(topicString, rounds, number_of_players = 3, generic_players=False)