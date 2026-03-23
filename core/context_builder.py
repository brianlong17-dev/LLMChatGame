from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.gameboard import GameBoard
    from agents.base_agent import BaseAgent
    from core.gameboard import RoundEntry


class ContextBuilder:
    
    def __init__(self, game_board: 'GameBoard'):
        self.game_board = game_board
        self.min_rounds_for_context = 3
        #some settings can probably move here
    
    def current_round_formatted(self, agent: 'BaseAgent'):
        return  self._formatted_round(self.game_board.current_round, agent)
    
    
    def get_full_context(self, agent: 'BaseAgent'):
        current_text = self.current_round_formatted(agent)
        rounds = self.game_board.current_phase_rounds()
        if len(rounds) < self.min_rounds_for_context:
            rounds = self.game_board.completed_round_entries[-self.min_rounds_for_context:]
        if len(rounds) == 0:
            rounds_string =  "This is the first round. There is no prior history. \n"
        else:
            rounds_string = f"### PAST {len(rounds)} ROUNDS  ###\n"
            rounds_string += "\n\n".join( self._formatted_round(r, agent) for r in rounds)
        context_string = (
            f"{rounds_string}"
            f"\n\n### CURRENT ROUND DIALOGUE ###\n"
            f"{current_text}"
        )
        return context_string 
            
    def phase_rounds_string(self, agent: 'BaseAgent'): #Used to make a phase to summarise
        return self._formatted_phase(self.game_board.phase_number, agent)
    
    def _formatted_phase(self, phase_number, agent):
        rounds = self.game_board.phase_rounds(phase_number)
        if len(rounds) == 0:
            return "This is the first round. There is no prior history."
        
        history_blocks = []
        for i, round in enumerate(rounds):
            block = (
                f"--- PHASE {phase_number} - ROUND {i + 1}---\n"
                f"{self._formatted_round(round, agent)}"
            )
            history_blocks.append(block)
        return "\n\n".join(history_blocks)
    
    def _round_header(self, round):
        return f"------- Phase: {round.phase_number}, Round: {round.round_number} --------"
    
    def _formatted_round(self, round: 'RoundEntry', agent: 'BaseAgent'):
        output = f"\n{self._round_header(round)}\n"
        if len(round.messages) == 0:
            return output + "No messages yet for round."
        
        for entry in round.messages:
            if entry.visibility_restriction == None:
                for message in entry.messages:
                    output += (f"\n{message['speaker']}: {message['message']}")
            else:
                if agent.name in entry.visibility_restriction:
                    names =  ", ".join(entry.visibility_restriction)
                    output += f"\n--------------- Private Conversation between {names} ----------------\n"
                    for message in entry.messages:
                        output += (f"\n{message['speaker']}: {message['message']}")
                    output += f"\n--------------- END OF Private Conversation between {names} ----------------\n"
        return output
    
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
        
   
        