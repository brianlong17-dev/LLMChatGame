from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from core.gameboard import GameBoard


class ContextBuilder:
    
    def __init__(self, game_board: 'GameBoard'):
        self.game_board = game_board
        #some settings can probably move here
    
    def current_round_formatted(self):
        return  self._format_dialogue_list(self.game_board.currentRound)
    
    def get_full_context(self):
        current_text = self.current_round_formatted()
        rounds_count = max(len(self.game_board.current_phase_rounds), self.game_board.full_rounds_text_amount)
        context_string = (
            f"### PAST {rounds_count} ROUNDS  ###\n"
            f"{self.formatted_recent_rounds(rounds_count)}\n\n"
            f"### CURRENT ROUND DIALOGUE ###\n"
            f"{current_text}"
        )
        return context_string 
            
    
    def _format_dialogue_list(self, dialogue_list):
        """Helper to turn a list of dicts into a readable string."""
        if not dialogue_list:
            return "No dialogue yet."
        return "\n".join([f"{entry['speaker']}: {entry['message']}" for entry in dialogue_list])
    
    def formatted_recent_rounds(self, count):
        
        if len(self.game_board.round_entries) == 0:
            return "This is the first round. There is no prior history."
        
        recent_rounds = list(self.game_board.round_entries)[-count:]
        history_blocks = []
        for i, round_data in enumerate(recent_rounds):
            past_round_num = self.game_board.round_number - len(recent_rounds) + i
            block = (
                f"--- ROUND {past_round_num} ARCHIVE ---\n"
                f"{self._format_dialogue_list(round_data)}"
            )
            history_blocks.append(block)
            
        return "\n\n".join(history_blocks)
    
    def phase_rounds_string(self):
        if len(self.game_board.current_phase_rounds) == 0:
            return "This is the first round. There is no prior history."
        history_blocks = []
        rounds = self.game_board.current_phase_rounds
        for i, round_data in enumerate(rounds):
            # Calculate the actual round number for the header
            
            block = (
                f"--- PHASE {self.game_board.phase_number} - ROUND {i + 1}---\n"
                f"{self._format_dialogue_list(round_data)}"
            )
            history_blocks.append(block)
        return "\n\n".join(history_blocks)
    
    def get_dashboard_string(self, agent_name: str) -> str:
        agent_scores = dict(self.game_board.agent_scores)
        """Generates a score dashboard."""
        if agent_name not in agent_scores:
            return "=== STATUS: ELIMINATED ===\nYou are dead. Observe the living."

        my_score = agent_scores[agent_name]
        
        # 1. Calculate Standings
        # Sort by score (descending)
        sorted_scores = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_scores[0][1] if sorted_scores else 0
        leaders = [name for name, score in agent_scores.items() if score == max_score]
        
        is_leader = agent_name in leaders
        points_behind = max_score - my_score

        # 2. Build the Visual Dashboard
        dash = []
        dash.append("=== REALITY CHECK DASHBOARD ===")
        overall_game_rules = self.game_board.phase_runner.overall_game_rules
        if overall_game_rules:
            dash.append("OVERALL GAME:")
            dash.append(overall_game_rules)
        
        # A. The Leaderboard (Clean List)
        dash.append("CURRENT STANDINGS:")
        for name, score in sorted_scores:
            marker = " <-- YOU" if name == agent_name else ""
            dash.append(f"- {name}: {score} points{marker}")
        
        dash.append("") # Empty line for spacing

        # B. The Narrative Status
        if is_leader:
            if len(leaders) > 1:
                tied_with = [l for l in leaders if l != agent_name]
                dash.append(f"STATUS: TIED FOR 1ST with {', '.join(tied_with)}.")
            else:
                dash.append("STATUS: YOU ARE WINNING.")
        else:
            dash.append("STATUS: YOU ARE LOSING.")
            dash.append(f"MATH: You are exactly {points_behind} points behind the leader.")

        # C. The Roster (Who is left?)
        # (Optional: You might not need this if everyone is in the leaderboard above, 
        # but strictly separating 'Dead' is useful)
        removed_agent_names = self.game_board.phase_runner.removed_agent_names()
        dead_str = ", ".join(removed_agent_names) if removed_agent_names else "None"
        dash.append(f"EVICTED PLAYERS: {dead_str} (Already gone. Do not plot against them)")
        dash.append(self.current_phase_progress())
        return "\n".join(dash)
    
    def current_phase_progress(self):
        string = ("===============================\n")
        string += ("CURRENT PHASE PROGRESS:")
        string +=  (self.game_board.phase_runner.get_phase_progress_string())
        string += ("\n===============================\n")
        return string
        
   
        