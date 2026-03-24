from agents.character_generation.characterGeneration import CharacterGenerator
from core.game_config import GameConfig
from core.phase_runner import PhaseRunner
from core.phase_recipe_factory import PhaseRecipeFactory
from agents.base_agent import *
from agents.gameMaster import GameMaster
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
        self.gameplay_config = GameConfig()
        self.phase_runner = PhaseRunner(self)
        
        
        self.agents = []
        self.dead_agents = []
            
    def initialiseGameBoard(self):
        self.gameBoard.initialize_agents(self.agents)
        self.gameBoard.phase_runner = self.phase_runner
        
    def eliminate_player(self, agent):
        self.agents.remove(agent)
        self.dead_agents.append(agent)
        
    def _select_debug_targets(self):
        debug_targets = ['Morty Smith', 'Lady Macbeth']
        target_found = False

        for agent in self.agents:
            if True: #agent.name in debug_targets:
                agent.debug_log = True
                target_found = True
                
        if not target_found and self.agents:
            self.agents[0].debug_log = True
                    
  
    def set_up_players(self, number_of_players, generic_players):
        #TODO this printing is temp
        #TODO this should move to its own thing... I think the simulation engine should be passed agents 
        print(PromptLibrary.line_break)
        if generic_players:
            self.agents = self.generator.genericPlayers(number_of_players)
        else:
            self.agents = self.generator.generate_random_debaters(number_of_players)
        self._select_debug_targets()
        print(PromptLibrary.line_break)
         
    def run(self, number_of_players = 2, generic_players=False, human_player = False):
        #player set up will move
        self.set_up_players(number_of_players, generic_players)
        if human_player:
            name = 'Brian' # input("Name?\n")
            human_player = Human(name)
            self.agents.append(human_player)
            
        self.initialiseGameBoard()
        
        while len(self.agents) > 1:
            phase = self.phase_factory.get_phase_recipe(self.gameBoard.phase_number + 1, len(self.agents), self.gameplay_config)
            self.phase_runner.run_phase(phase)
        #------------Fin------------#
        self.gameBoard.game_sink.on_game_over(self.agents[0].name)
  
           
