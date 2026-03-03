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
from core.console_renderer import ConsoleRenderer
from core.game_config import GameConfig
from core.phases import PhaseRecipe, PhaseRecipeFactory, PhaseRecipeFactoryDefault
from agents.base_agent import *
from agents.gameMaster import GameMaster
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from gameplay_management.unified_controller import UnifiedController
from models.player_models import *
from .gameboard import GameBoard
 
    
class SimulationEngine:
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-lite",
        higher_model_name: str = "gemini-2.5-flash",
        number_of_players = 5,
        phase_factory = PhaseRecipeFactoryDefault
    ):
        load_dotenv()
        self.client = instructor.from_provider('google/' + model_name, api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name
        self.higher_model_name = higher_model_name
        self.game_master = GameMaster(self.client, model_name, higher_model_name=self.higher_model_name)
        self.generator = CharacterGenerator(self.client, self.model_name, higher_model_name=self.higher_model_name)
        self.phase_number = 0
        self.gameBoard = GameBoard(self.game_master)
        self.game_manager = UnifiedController(self.gameBoard, self)
        self.phase_factory = phase_factory
        self.gameplay_config = GameConfig()
            
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
    
    def _validate_immunity(self, immunity_type, immunity_names):
        if not isinstance(immunity_names, list):
                raise TypeError(
                        f"Immunity '{immunity_type.display_name}' must return list[str], got {type(immunity_names).__name__}"
                    )
        if not all(isinstance(name, str) for name in immunity_names):
            raise TypeError(
                f"Immunity '{immunity_type.display_name}' must return list[str], got non-string values: {immunity_names!r}"
            )
        active_player_names = {agent.name for agent in self.agents}
        invalid_names = [name for name in immunity_names if name not in active_player_names]
        if invalid_names:
            raise ValueError(
                f"Immunity '{immunity_type.display_name}' returned unknown player name(s): {invalid_names}"
            )
        
    def runPhase(self, recipe: PhaseRecipe):
        
        self.printPhaseHeader()
        host_intro, system_summary = recipe.phase_intro_string(self.phase_number, len(self.agents), self.game_manager)
        self.gameBoard.host_broadcast(host_intro)
        self.gameBoard.broadcast_public_action("", system_summary, "SYS")
        
        for _ in range(recipe.pre_game_discussion_rounds):  
            self.trigger_new_round()
            self.game_manager.run_discussion_round()
        
        if recipe.mini_game:
            if issubclass(recipe.mini_game, GameMechanicsMixin):
                self.trigger_new_round()
                game_name = recipe.mini_game.display_name(self.game_manager)
                game_rules = recipe.mini_game.rules_description(self.game_manager)
                self.gameBoard.system_broadcast(f"🎲 GAME EVENT: {game_name}\n")
                self.gameBoard.system_broadcast(f"GAME RULES: {game_rules}\n")
                recipe.mini_game.run_game(self.game_manager)
            else:
            
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
                immune_players: list[str] = []
                
                if recipe.immunity_types:
                    for immunity_type in recipe.immunity_types:
                        result = immunity_type.run_immunity(self.game_manager)
                        self._validate_immunity(immunity_type, result)
                        immune_players.extend(result)
                immune_players = list(dict.fromkeys(immune_players))
            self.gameBoard.system_broadcast(f"🗳️ - TRIGGERING VOTE - {recipe.vote_type.display_name(self.game_manager)}\n")
                                          #  f"- {recipe.vote_type.rules_description(self.game_manager)}")
                                          # rules should be handled in game by host.
            
            recipe.vote_type.run_vote(self.game_manager, immunity_players=immune_players)
        
        
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
         
    def run(self, number_of_players = 2, generic_players=False):
        self.set_up_players(number_of_players, generic_players)
        self.initialiseGameBoard()
        
        game_introduction  = self.phase_factory.game_intro()
        self.gameBoard.host_broadcast(f"\n{game_introduction}")
        while len(self.agents) > 1:
            self.phase_number += 1
            phase = self.phase_factory.get_phase_recipe_test_immunities(self.phase_number, len(self.agents), self.gameplay_config)
            self.runPhase(phase)
            
        print(f"🏆 FINAL SURVIVOR: {self.agents[0].name}")
        
  
           
