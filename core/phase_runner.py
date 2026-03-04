from typing import TYPE_CHECKING



if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine
    from core.phases import PhaseRecipe



    
class PhaseRunner:
    def __init__(self, simulation_engine: 'SimulationEngine'):
        self.simulation_engine = simulation_engine
        
        
    def trigger_new_round(self, game_baord):
        game_baord.system_broadcast(game_baord.agent_scores)
        game_baord.newRound()
        
    def printPhaseHeader(self, game_board):
        #TODO
        game_board.game_sink.on_phase_header
        
    def run_phase(self, recipe: 'PhaseRecipe'):
        game_board = self.simulation_engine.gameBoard
        game_manager = self.simulation_engine.game_manager
        self.printPhaseHeader(game_board)
        
        host_intro, system_summary = recipe.phase_intro_string(self.simulation_engine.phase_number, len(self.simulation_engine.agents), self.simulation_engine.game_manager)
        
        game_board.host_broadcast(host_intro)
        game_board.broadcast_public_action("", system_summary, "SYS")
        #above can move
        
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
            if len(self.agents) <= 1:
                break #already over
            self.trigger_new_round(game_board)
            round_number = recipe.post_vote_discussion_rounds - i
            game_board.host_broadcast(f"You have {round_number} round(s) to discuss, before the next phase begins")
            game_manager.run_discussion_round()
                
        
        return
    
    #move
    def _validate_immunity(self, immunity_type, immunity_names):
        #goes without saying this has no business here
        if not isinstance(immunity_names, list):
                raise TypeError(
                        f"Immunity '{immunity_type.display_name(self.simulation_engine.game_master)}' must return list[str], got {type(immunity_names).__name__}"
                    )
        if not all(isinstance(name, str) for name in immunity_names):
            raise TypeError(
                f"Immunity '{immunity_type.display_name(self.simulation_engine.game_master)}' must return list[str], got non-string values: {immunity_names!r}"
            )
        active_player_names = {agent.name for agent in self.simulation_engine.agents}
        invalid_names = [name for name in immunity_names if name not in active_player_names]
        if invalid_names:
            raise ValueError(
                f"Immunity '{immunity_type.display_name}' returned unknown player name(s): {invalid_names}"
            )
      