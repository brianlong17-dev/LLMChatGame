from typing import TYPE_CHECKING

from gameplay_management.immunities.immunity_mechanicsMixin import ImmunityMechanicsMixin



if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine
    from core.phases import PhaseRecipe



    
class PhaseRunner:
    def __init__(self, simulation_engine: 'SimulationEngine'):
        self.simulation_engine = simulation_engine
        
        
    def trigger_new_round(self, game_baord):
        game_baord.system_broadcast(game_baord.agent_scores)
        game_baord.newRound()
        
    def printPhaseHeader(self, game_board, phase_number):
        #TODO
        game_board.game_sink.on_phase_header(phase_number)
        
    def run_vote_round_with_immunity_types(self, round, game_manager, immunity_types):
        immune_players = []
        if immunity_types:
            for immunity_type in immunity_types:
                result = immunity_type.run_immunity(game_manager) #TODO run_immunity should validate
                immune_players.extend(result)
        immune_players = list(dict.fromkeys(immune_players)) #remove any dupes
        round.run_vote(game_manager, immunity_players=immune_players)

    
    
    def run_round(self, round, game_board, game_manager, immunity_types):
        
        game_board.newRound()
        if round.is_vote():
            return self.run_vote_round_with_immunity_types(round, game_manager, immunity_types)
        round.run_game(game_manager)
        game_board.system_broadcast(game_board.agent_scores)
        game_board.endRound()
        #system sumamry 
        #print scores.
        
        
    def run_phase(self, recipe: 'PhaseRecipe'):
        game_board = self.simulation_engine.gameBoard
        game_manager = self.simulation_engine.game_manager
        
        
        game_board.game_sink.on_phase_header(self.simulation_engine.phase_number)
        host_intro = recipe.phase_intro_string(self.simulation_engine.phase_number, len(self.simulation_engine.agents), self.simulation_engine.game_manager)
        system_summary = recipe.phase_summary_string(game_manager)
        game_board.host_broadcast(host_intro)
        game_board.broadcast_public_action("", system_summary, "SYS") #these need their own thing
        
        
        #above can move
        for round in recipe.rounds:
            self.run_round(round, game_board, game_manager, recipe.immunity_types) #this isnt right. you shouldnt send this every time.
         
        
        return
        for _ in range(recipe.pre_game_discussion_rounds):  
            self.trigger_new_round(game_board)
            self.simulation_engine.game_manager.run_discussion_round()
        
        if recipe.mini_game:
            self.trigger_new_round(game_board)
            game_name = recipe.mini_game.display_name(game_manager)
            game_rules = recipe.mini_game.rules_description(game_manager)
            game_board.system_broadcast(f"🎲 GAME EVENT: {game_name}\n")
            game_board.system_broadcast(f"GAME RULES: {game_rules}\n")
            recipe.mini_game.run_game(game_manager)
            
        
        for _ in range(recipe.pre_vote_discussion_rounds):
            self.trigger_new_round(game_board)
            game_manager.run_discussion_round()
        
        if recipe.vote_type:
            
            self.trigger_new_round(game_board)
            if recipe.vote_type:
                immune_players: list[str] = []
                
                if recipe.immunity_types:
                    for immunity_type in recipe.immunity_types:
                        result = immunity_type.run_immunity(game_manager)
                        self._validate_immunity(immunity_type, result)
                        immune_players.extend(result)
                immune_players = list(dict.fromkeys(immune_players))
            game_board.system_broadcast(f"🗳️ - TRIGGERING VOTE - {recipe.vote_type.display_name(game_manager)}\n")
                                          #  f"- {recipe.vote_type.rules_description(self.game_manager)}")
                                          # rules should be handled in game by host.
            
            recipe.vote_type.run_vote(game_manager, immunity_players=immune_players)
        
        
        for i in range(recipe.post_vote_discussion_rounds):
            if len(self.simulation_engine.agents) <= 1:
                break #already over
            self.trigger_new_round(game_board)
            round_number = recipe.post_vote_discussion_rounds - i
            game_board.host_broadcast(f"You have {round_number} round(s) to discuss, before the next phase begins")
            game_manager.run_discussion_round()
                
        
        return
    
    