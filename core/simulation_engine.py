import os
import instructor
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents.character_generation.characterGeneration import CharacterGenerator
from core.game_config import GameConfig
from core.phase_runner import PhaseRunner
from core.sinks.game_sink import GameEventSink
from core.phases import PhaseRecipe, PhaseRecipeFactory, PhaseRecipeFactoryDefault
from agents.base_agent import *
from agents.gameMaster import GameMaster
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from gameplay_management.unified_controller import UnifiedController
from models.player_models import *
from .gameboard import GameBoard
from agents.human_player import Human
 
    
class SimulationEngine:
    def __init__(self, game_board: GameBoard, game_master: GameMaster, generator: CharacterGenerator, 
                 phase_factory: PhaseRecipeFactory,):
        
        
        self.game_master = game_master
        
        self.phase_factory = phase_factory
        
        self.gameBoard = game_board
        self.generator = generator
        self.game_manager = UnifiedController(self.gameBoard, self)
        self.gameplay_config = GameConfig()
        self.phase_runner = PhaseRunner(self)
        self.phase_number = 0
        
            
    def initialiseGameBoard(self):
        self.gameBoard.initialize_agents(self.agents)
    
    def runPhase(self, recipe: PhaseRecipe):
        self.phase_runner.run_phase(recipe)
  
    def set_up_players(self, number_of_players, generic_players):
        #TODO this printing is temp
        #TODO this should move to its own thing... I think the simulation engine should be passed agents 
        print(PromptLibrary.line_break)
        if generic_players:
            self.agents = self.generator.genericPlayers(number_of_players)
        else:
            self.agents = self.generator.generate_balanced_cast(number_of_players)
        print(PromptLibrary.line_break)
         
    def run(self, number_of_players = 2, generic_players=False, human_player = False):
        #player set up will move
        self.set_up_players(number_of_players, generic_players)
        if human_player:
            name = 'Brian' # input("Name?\n")
            human_player = Human(name)
            self.agents.append(human_player)
            self.gameBoard.has_human_player = True
            
        self.initialiseGameBoard()
        
        #-----------Intro------------#
        self.gameBoard.game_sink.on_game_intro(self.phase_factory.game_intro())
        
        while len(self.agents) > 1:
            self.phase_number += 1
            phase = self.phase_factory.get_phase_recipe(self.phase_number, len(self.agents), self.gameplay_config)
            self.runPhase(phase)
        #------------Fin------------#
        self.gameBoard.game_sink.on_game_over(self.agents[0].name)
  
           
