from collections import deque
from typing import Union
from agents.base_agent import BaseAgent
from .console_renderer import ConsoleRenderer

class GameBoard:
    def __init__(self, game_master):
        self.full_rounds_text_amount = 3 #we get current round and past round
        self.game_master = game_master
        self.agent_names = []
        self.round_number = 0
        self.turn_number = 0
        self.execution_style = False
        self.history = []
        self.currentRound = []
        self.round_entries = deque(maxlen=10)#dont rly need
        self.round_summaries = deque(maxlen=50)
        self.agent_scores: dict[str, int] = {}
        self.agent_response_allowed: dict[str, bool] = {}
        self.agent_forms: dict[str, str] = {}
        self.removed_agent_names = []
    
    def get_agent_score(self, agent_name: str) -> int:
        if agent_name not in self.agent_scores:
            raise RuntimeError(f"Missing score for active player '{agent_name}'")
        return self.agent_scores[agent_name]


    def new_turn_print(self):
        self.turn_number += 1
        ConsoleRenderer.print_turn_header(self.turn_number)
            
    def newRound(self):
        #This will move to the simulator
        #self.print_leaderboard()
        
        self.round_number += 1
        self.round_entries.append(list(self.currentRound))
        roundSummary = self.game_master.summariseRound(self)
        
        roundSummaryString = "\n".join([f"{key}: {value}" for key, value in roundSummary])
        
        self.round_summaries.append(roundSummary.round_summary)
        ConsoleRenderer.print_private("SUMMARY", f"{roundSummary.round_summary} \n", color_name = "YELLOW")
        self.currentRound.clear()
        self.broadcast_public_action("SYSTEM", f"BEGIN ROUND {self.round_number}")
    
    def system_broadcast_no_name(self, msg):
        return self.gameBoard.broadcast_public_action("", msg, "SYS")
    
    def broadcast_public_action(self, speaker: Union[str, BaseAgent], message: str, color: str = ""):
        display_name, _ = ConsoleRenderer.get_name_and_color(speaker)
        self._update_history(display_name, message)
        ConsoleRenderer.print_public_action(speaker, message, color)
    
    def system_broadcast(self, message):
        self.broadcast_public_action("SYSTEM", message)
        
    def host_broadcast(self, message):
        self.broadcast_public_action("HOST", message)
        
    def _format_dialogue_list(self, dialogue_list):
        """Helper to turn a list of dicts into a readable string."""
        if not dialogue_list:
            return "No dialogue yet."
        return "\n".join([f"{entry['speaker']}: {entry['message']}" for entry in dialogue_list])
    
    def history_text(self):
        """Returns the compressed/summarized history of past rounds."""
        if len(self.round_entries) == 0:
            return "This is the first round. There is no prior history."
        recent_rounds = list(self.round_entries)[-self.full_rounds_text_amount:]
        history_blocks = []
        for i, round_data in enumerate(recent_rounds):
            # Calculate the actual round number for the header
            past_round_num = self.round_number - len(recent_rounds) + i
            block = (
                f"--- ROUND {past_round_num} ARCHIVE ---\n"
                f"{self._format_dialogue_list(round_data)}"
            )
            history_blocks.append(block)
            
        return "\n\n".join(history_blocks)
    
    def window_text(self):
        if not self.round_entries:
            return ""
        return "\n".join([f"{m['speaker']}: {m['message']}" for m in self.round_entries])
    
    def get_full_context(self):
        """Combines them with clear markdown headers for the LLM to read."""
        current_text = self._format_dialogue_list(self.currentRound)
        round_summaries_formatted = ("\n".join(list(self.round_summaries)))
        context_string = (
            f"### PAST ROUND SUMMARIES  ###\n"
            f"{round_summaries_formatted}\n\n"
            f"### PAST {self.full_rounds_text_amount} ROUNDS  ###\n"
            f"{self.history_text()}\n\n"
            f"### CURRENT ROUND DIALOGUE ###\n"
            f"{current_text}"
        )
        #print(f"XXX: {context_string} \n YYY" )
        return context_string 
        
    def remove_agent_state(self, agent_name: str):
        """Cleans up the dictionaries when an agent dies."""
        self.removed_agent_names.append(agent_name)
        self.agent_names.remove(agent_name)
        self.agent_scores.pop(agent_name, None)
        self.agent_forms.pop(agent_name, None)
        self.agent_response_allowed.pop(agent_name, None)

    def initialize_agents(self, agent_list):
        for agent in agent_list:
            self.add_agent_state(agent.name, agent.form, 0)
            
    def add_agent_state(self, agent_name: str, form: str, initial_score: int = None):
        """Initializes dictionaries for a newly born agent."""
        self.agent_names.append(agent_name)
        #adding a new player midway gets average points. Redundant TODO remove 
        if initial_score == None:
            current_scores = list(self.agent_scores.values())
            initial_score = int(sum(current_scores) / len(current_scores)) if current_scores else 0
        self.agent_scores[agent_name] = initial_score
        self.agent_forms[agent_name] = form
        self.agent_response_allowed[agent_name] = True  
        
    def _update_history(self, player_name, message):
        entry = {"speaker": player_name, "message": message}
        self.currentRound.append(entry)
    
    def print_leaderboard(self):
        # 1. Sort by score (highest to lowest)
        scores = self.agent_scores
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        print("\n" + "="*30)
        print(f"{'RANK':<6} {'AGENT':<15} {'SCORE':>5}")
        print("-" * 30)
        for rank, (agent, score) in enumerate(sorted_scores, 1):
            # Add a crown for the leader
            prefix = "👑" if rank == 1 else "  "
            # Check if allowed to speak
            #is_allowed = self.agent_response_allowed.get(agent, True)
            #status = "\033[92m🟢 SPEAKING\033[0m" if is_allowed else "\033[91m🔴 SILENCED\033[0m"
            
            print(f"{rank:<6} {prefix} {agent:<13} {score:>5}  ") #{status}
            #print(f"      \033[3m{self.agent_forms.get(agent, 'Unknown form')}\033[0m")
            
        print("="*45 + "\n")
    
    def get_dashboard_string(self, agent_name: str) -> str:
        """Generates a hard-facts reality check for an agent's system prompt."""
        if agent_name not in self.agent_scores:
            return "=== STATUS: ELIMINATED ===\nYou are dead. Observe the living."

        my_score = self.agent_scores[agent_name]
        
        # 1. Calculate Standings
        # Sort by score (descending)
        sorted_scores = sorted(self.agent_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_scores[0][1] if sorted_scores else 0
        leaders = [name for name, score in self.agent_scores.items() if score == max_score]
        
        is_leader = agent_name in leaders
        points_behind = max_score - my_score

        # 2. Build the Visual Dashboard
        dash = []
        dash.append("=== REALITY CHECK DASHBOARD ===")
        
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
        dead_str = ", ".join(self.removed_agent_names) if self.removed_agent_names else "None"
        dash.append(f"GRAVEYARD: {dead_str} (Do not plot against them)")
        
        dash.append("===============================")
        return "\n".join(dash)
        
        
    def append_agent_points(self, agent_name, points):
        new_score = max(0, self.agent_scores[agent_name] + points)
        self.agent_scores[agent_name] = new_score
             
    def resetScores(self):
        for entry in self.agent_scores:
            self.agent_scores[entry] = 0
                
        