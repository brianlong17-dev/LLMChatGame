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
import instructor
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents.characterGeneration import CharacterGenerator
from core.gameplay_definitions_config import *
from core.phases import PhaseRecipe, PhaseRecipeFactory
from agents.base_agent import *
from agents.gameMaster import GameMaster
from gameplay_management.unified_controller import UnifiedController
from models.player_models import *
from .gameboard import GameBoard
 
    
class SimulationEngine:
    def __init__(self, model_name: str = "gemini-2.5-flash-lite", number_of_players = 5):
        load_dotenv()
        self.client = instructor.from_provider('google/' + model_name, api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name
        self.game_master = GameMaster(self.client, model_name)
        self.generator = CharacterGenerator(self.client, self.model_name)
        self.phase_number = 0
        self.gameBoard = GameBoard(self.game_master)
        self.game_manager = UnifiedController(self.gameBoard, self)
        
    def initialiseGameBoard(self):
        self.gameBoard.initialize_agents(self.agents)
    
    def printPhaseHeader(self):
        ConsoleRenderer.print_system_private(PromptLibrary.line_break)
        ConsoleRenderer.print_system_private(f"PHASE: {self.phase_number}")
        ConsoleRenderer.print_system_private(PromptLibrary.line_break)
    
    def trigger_new_round(self):
        #we want to print the score at the end of the round. 
        #We want to print this so the summariser can see it
        self.gameBoard.system_broadcast(self.gameBoard.agent_scores)
        self.gameBoard.newRound()
        
        
    def runPhase(self, recipe: PhaseRecipe):
        
        self.printPhaseHeader()
        host_intro, system_summary = recipe.phase_intro_string(self.phase_number, len(self.agents))
        self.gameBoard.host_broadcast(host_intro)
        self.gameBoard.broadcast_public_action("", system_summary, "SYS")
        
        for _ in range(recipe.pre_game_discussion_rounds):  
            self.trigger_new_round()
            self.game_manager.run_discussion_round()
        
        if recipe.mini_game:
            self.trigger_new_round()
            #this printing has to be moved.
            self.gameBoard.system_broadcast(f"🎲 GAME EVENT: {recipe.mini_game.display_name}\n")
            #self.gameBoard.system_broadcast(recipe.mini_game.rules_description)
            #The game has its own print? It's a live print I guess its better?
            recipe.mini_game.execute_game(self.game_manager)
        
        for _ in range(recipe.pre_vote_discussion_rounds):
            self.trigger_new_round()
            self.game_manager.run_discussion_round()
        
        if recipe.vote_type:
            
            self.trigger_new_round()
            if recipe.vote_type:
                immune_players = [] # Use a standard list!
                
                if recipe.immunity_types:
                    for immunity in recipe.immunity_types:
                        result = immunity.execute_game(self.game_manager)
                        if isinstance(result, list):
                            immune_players.extend(result)
                        else:
                            immune_players.append(result)
            self.gameBoard.system_broadcast(f"\n🗳️ TRIGGERING VOTE: {recipe.vote_type.display_name}")
            self.gameBoard.system_broadcast(recipe.vote_type.rules_description)
            
            recipe.vote_type.execute_game(self.game_manager, immunity_players=immune_players)
        
        
        for i in range(recipe.post_vote_discussion_rounds):
            if len(self.agents) <= 1:
                break #already over
            self.trigger_new_round()
            round_number = recipe.post_vote_discussion_rounds - i
            self.gameBoard.host_broadcast(f"You have {round_number} round(s) to discuss, before the next phase begins")
            self.game_manager.run_discussion_round()
                
        
        return
  
    def set_up_players(self, number_of_players, generic_players):
        print(PromptLibrary.line_break)
        if generic_players:
            self.agents = self.generator.genericPlayers(number_of_players)
        else:
            #self.agents = [self.generator.generate_random_debater() for _ in range(number_of_players)]
            self.agents = self.generator.generate_balanced_cast(number_of_players)
        print(PromptLibrary.line_break)
         
    def run(self, game_introduction: str, rounds_per_discussion_phase=1, number_of_players = 2, generic_players=False):
        #print(f"\n🚀 Simulation Started: {topic}\n" + "="*50)
        self.set_up_players(number_of_players, generic_players)
        self.initialiseGameBoard()
        
        
        self.gameBoard.host_broadcast(f"\n{game_introduction}")
        while len(self.agents) > 1:
            self.phase_number += 1
            self.runPhase(PhaseRecipeFactory.get_phase_recipe(self.phase_number, len(self.agents)))
            
        print(f"🏆 FINAL SURVIVOR: {self.agents[0].name}")
        
  
           