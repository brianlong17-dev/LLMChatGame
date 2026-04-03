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
        

    @property
    def game_board(self):
        return self.simulation_engine.gameBoard
    
    def _cfg(self):
        return self.simulation_engine.gameplay_config

    def agent_names(self):
        return [agent.name for agent in self.simulation_engine.agents]
    
    def removed_agent_names(self):
        return [agent.name for agent in self.simulation_engine.dead_agents]

    def run_vote_round_with_immunity_types(self, round_class, immunity_types):
        immune_players = []
        if immunity_types:
            for immunity_type in immunity_types:
                result = immunity_type(self.game_board, self.simulation_engine).run_immunity()
                immune_players.extend(result)
        immune_players = list(dict.fromkeys(immune_players)) #remove any dupes
        round_class(self.game_board, self.simulation_engine).run_vote(immunity_players=immune_players)

    
    def get_phase_progress_string(self):
        return self.current_recipe.phase_progress_string(self._cfg(), self.current_round_index)

    def _introduce_phase(self):
        cfg = self._cfg()
        host_intro = self.current_recipe.phase_intro_string(self.game_board.phase_number,
                                    len(self.agent_names()), cfg)
        system_phase_summary = self.current_recipe.phase_summary_string(cfg)
        round_names = [r.display_name(cfg) for r in self.current_recipe.rounds]

        self.game_board.host_broadcast(host_intro)
        self.game_board.system_broadcast(system_phase_summary, private = True)
        self.game_board.game_sink.on_phase_rounds(round_names)
        
    def _introduce_game(self):
        host_intro = self.simulation_engine.phase_factory.game_intro()
        self.game_board.game_sink.on_game_intro(host_intro)
        
    def run_round(self, round, immunity_types):
        self.current_round_index += 1
        self.game_board.newRound()
        self.game_board.game_sink.on_phase_round_index(self.current_round_index - 1)
        if self.game_board.phase_number == 1 and self.current_round_index == 1:
            self._introduce_game()
        if self.current_round_index == 1:
            self._introduce_phase()
            
        if round.is_vote():
            self.run_vote_round_with_immunity_types(round, immunity_types)
        else:
            round(self.game_board, self.simulation_engine).run_game()
        
        #self.game_board.system_broadcast(self.game_board.agent_scores)
        round_summary = self.simulation_engine.game_master.summariseRound(self.game_board)
        
        self.game_board.endRound(round_summary)

        
    def run_phase(self, recipe: 'PhaseRecipe'):
        
        if recipe.overall_game_rules:
            self.overall_game_rules = recipe.overall_game_rules
            
        self.current_round_index = 0

        cfg = self._cfg()
        for method, args in recipe.config_mutations:
            getattr(cfg, method)(*args)

        self.current_recipe = recipe
        self.game_board.new_phase()
        for round in recipe.rounds:
            self.run_round(round, recipe.immunity_types)
        
        
        agents = self.simulation_engine.agents + self.simulation_engine.dead_agents
        
        with ThreadPoolExecutor(max_workers=min(32, len(agents))) as executor:
            for agent in agents:
                executor.submit(agent.summarise_phase, self.game_board)
                
            
        self.game_board.endPhase()
  
    