from prompts.prompts import PromptLibrary


class UserContent:
    
    @classmethod
    def render(cls, agent, game_board, turn_instruction, game_history_override) -> str:
        #TODO the game_history_override -- eventually will have different context objects that call different render methods
        dash = []
        dashboard = game_board.context_builder.get_dashboard_string(agent)
        #TODO append agent.phase_strategy_notes
        dash.append(dashboard)
      
        if game_history_override:
            dash.append(game_history_override)
        else:
            cls.append_game_context(dash, agent, game_board)
            
        dash.append("=== YOUR TURN ===")
        if turn_instruction:
            dash.append(f"({turn_instruction})")
            
        return "\n\n".join(dash)
    
    
    
    @classmethod
    def append_game_context(cls, dash, agent, game_board):
        summaries = agent.phase_summaries_string()
        cb = game_board.context_builder
        anchor, other_player_message_found = cb._recency_anchor(agent)
        
        current_round = cb.current_round_formatted(agent, anchor, other_player_message_found)
        previous_rounds = cb.previous_rounds_formatted(agent, anchor, other_player_message_found)
        
        if summaries:
            dash.append("=== PHASE SUMMARIES ===")
            dash.append(summaries)
        if previous_rounds:
            #header included in method
            dash.append(previous_rounds)
        dash.append("=== CURRENT ROUND ===")
        dash.append(current_round)
        
    
        
        
    