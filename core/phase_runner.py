from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from gameplay_management.immunities.immunity_mechanicsMixin import ImmunityMechanicsMixin



if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine
    from core.phase_recipe import PhaseRecipe



    
class PhaseRunner:
    def __init__(self, simulation_engine: 'SimulationEngine'):
        self.simulation_engine = simulation_engine
        self.current_recipe = None
        self.current_round_index = 0
        self.overall_game_rules = ""
        self.set_up()
        
    def set_up(self):
        self.game_board = self.simulation_engine.gameBoard
        self.game_manager = self.simulation_engine.game_manager

    def agent_names(self):
        return [agent.name for agent in self.simulation_engine.agents]
    
    def removed_agent_names(self):
        return [agent.name for agent in self.simulation_engine.dead_agents]

    def run_vote_round_with_immunity_types(self, round, immunity_types):
        immune_players = []
        if immunity_types:
            for immunity_type in immunity_types:
                result = immunity_type.run_immunity(self.game_manager) #TODO run_immunity should validate
                immune_players.extend(result)
        immune_players = list(dict.fromkeys(immune_players)) #remove any dupes
        round.run_vote(self.game_manager, immunity_players=immune_players)

    
    def get_phase_progress_string(self):
        return self.current_recipe.phase_progress_string(self.game_manager,
                                                         self.current_round_index)
        
    def run_round(self, round, immunity_types):
        self.current_round_index += 1
        self.game_board.newRound()
        if round.is_vote():
            self.run_vote_round_with_immunity_types(round, immunity_types)
        else:
            round.run_game(self.game_manager)
        
        #self.game_board.system_broadcast(self.game_board.agent_scores)
        round_summary = self.simulation_engine.game_master.summariseRound(self.game_board)
        
        self.game_board.endRound(round_summary)

        
    def run_phase(self, recipe: 'PhaseRecipe'):
        
        if recipe.overall_game_rules:
            self.overall_game_rules = recipe.overall_game_rules
            
        self.current_round_index = 0
        self.set_up() #this is in case the game manager or board wasn't instanciated on the simulation engine yet...
        
        self.current_recipe = recipe 
        self.game_board.new_phase() 
        
        host_intro = self.current_recipe.phase_intro_string(self.game_board.phase_number, 
                                    len(self.agent_names()), self.game_manager)
        system_phase_summary = self.current_recipe.phase_summary_string(self.game_manager)
        
        self.game_board.host_broadcast(host_intro)
        self.game_board.system_broadcast(system_phase_summary, private = True)
        
        
        
        for round in recipe.rounds:
            self.run_round(round, recipe.immunity_types)
        
        
        agents = self.simulation_engine.agents
        with ThreadPoolExecutor(max_workers=min(32, len(agents))) as executor:
            for agent in agents:
                executor.submit(agent.summarise_phase, self.game_board)
                
            
        self.game_board.endPhase()
  
    