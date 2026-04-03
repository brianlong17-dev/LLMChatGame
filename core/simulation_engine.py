from __future__ import annotations
from typing import TYPE_CHECKING

from core.game_config import GameConfig
from core.phase_runner import PhaseRunner
from agents.human_player import Human

if TYPE_CHECKING:
    from agents.character_generation.characterGeneration import CharacterGenerator
    from core.phase_recipe_factory import PhaseRecipeFactory
    from agents.gameMaster import GameMaster
    from core.gameboard import GameBoard
    from agents.player import Debater
    
 
    
class SimulationEngine:
    def __init__(self, agents: list[Debater], game_board: GameBoard, game_master: GameMaster, generator: CharacterGenerator, 
                 phase_factory: PhaseRecipeFactory,):
        
        
        self.game_master = game_master
        self.phase_factory = phase_factory
        
        self.gameBoard = game_board
        self.generator = generator
        self.gameplay_config = GameConfig()
        self.phase_runner = PhaseRunner(self)
        
        
        self.agents = agents
        self._select_debug_targets()
        self.dead_agents = []
            
    def initialiseGameBoard(self):
        self.gameBoard.initialize_agents(self.agents)
        self.gameBoard.phase_runner = self.phase_runner
        
    def eliminate_player(self, agent):
        agent.game_over = True
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
                    

    def run(self, human_player_name = ""):

        if human_player_name:
            #name = 'Brian' # input("Name?\n")
            human_player = Human(human_player_name)
            self.agents.append(human_player)
            
        self.initialiseGameBoard()
        
        while len(self.agents) > 1:
            phase = self.phase_factory.get_phase_recipe(self.gameBoard.phase_number + 1, len(self.agents), self.gameplay_config)
            self.phase_runner.run_phase(phase)
        #------------Fin------------#
        self.gameBoard.game_sink.on_game_over(self.agents[0].name)
        #here 
        self._post_game_interview()
        
    def _post_game_interview(self):
        pass
        #Would you like to select a player to speak to?
        #human input, select a name-
        #here you can ask them a question
        #we put the question to them via private conversation- 
        #the conversation is added to a dictionary with agent- conv id keys
        #Between host and player- maybe host should get a different name.
        #or we could drum up a new human agent.
        #ask them a question:
        #the person responds
        #ask another question - yes - no
        #if no select another name - outer loop
        #if yes continue inner loop
  
           
