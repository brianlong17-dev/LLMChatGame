from collections import deque


class GameBoard:
    COLORS = {
            "RED": "\033[91m",
            "GREEN": "\033[92m",
            "BLUE": "\033[94m",
            "YELLOW": "\033[93m",
            "RESET": "\033[0m"
        }
    
    def __init__(self, game_master, agent_names):
        self.full_rounds_text_amount = 2
        self.game_master = game_master
        self.agent_names = []
        self.judge = None
        self.round_number = 0
        self.turn_number = 0
        self.history = []
        self.currentRound = []
        self.round_entries = deque(maxlen=30)
        self.round_summaries = deque(maxlen=5)
        self.agent_scores: dict[str, int] = {}
        self.agent_response_allowed: dict[str, bool] = {}
        self.agent_forms: dict[str, str] = {}
        for agent_name in agent_names:
            self.add_agent_state(agent_name, 'blob')
        
            
    def newRound(self):
        self.round_number += 1
        self.round_entries.append(list(self.currentRound))
        #print(f"SSS: {self.round_entries}")
        #print(f"PPP: {list(self.round_entries)[-2:]}")
        roundSummary = self.game_master.summariseRound(self)
        roundSummaryString = "\n".join([f"{key}: {value}" for key, value in roundSummary])
        self.round_summaries.append(roundSummary)
        self.privatePrint("SUMMARY", f"{roundSummaryString}", color = "YELLOW")
        self.currentRound.clear()
        self.print_and_save("SYSTEM", f"BEGIN ROUND {self.round_number}")
        
        
    def process_turn(self, player):
        result = player.take_turn(self)
        self.turn_number += 1
        color = player.color
        
        print(f"\n\n\033[1m[TURN {self.turn_number}]\033[0m")
        self.print_and_save(player.name, result['public_text'], color=color)
        for key in result['private_text']:
            text = f"{key} : {result['private_text'][key]}"
            self._print(player.name, text, is_private = True, color=color)
        return result
    
    def _print(self, player_name, public_message: str, color = "", is_private = False, print_name = False):
        reset = self.COLORS["RESET"]
        if player_name == "SYSTEM":
            color = "GREEN"
        color_code = self.COLORS.get(color, reset)
        bold = "\033[1m"
        italic = "\033[3m" if is_private else ""
        if print_name:
            print(f"{bold}{color_code}{player_name}{reset}")
        print(f"{color_code}{italic}{public_message}{reset}")
    
    def privatePrint(self, player_name, public_message: str, color = None):
        return(self._print(player_name, public_message, color, is_private = True, print_name = True))
               
    def print_and_save(self, player_name, public_message: str, color = None):
        
        self._print(player_name, public_message, color, print_name = True)
        self._update_history(player_name, public_message)
        
    def history_text(self):
        """Returns the compressed/summarized history of past rounds."""
        if len(self.round_entries) == 0:
            return "This is the first round. There is no prior history."
        recent_rounds = list(self.round_entries)[-self.full_rounds_text_amount:]
        history_lines = []
        for i, round_data in enumerate(recent_rounds):
            # Optional: Add a header for each past round to help the LLM understand timeline
            history_lines.append(f"\n--- Past Round ---")
            for entry in round_data:
                history_lines.append(f"{entry['speaker']}: {entry['message']}")
        
        # Assuming game_summary holds strings of summarized past rounds
        return "\n".join(history_lines)
    
    def window_text(self):
        if not self.round_entries:
            return ""
        return "\n".join([f"{m['speaker']}: {m['message']}" for m in self.round_entries])
    
    def get_full_context(self):
        """Combines them with clear markdown headers for the LLM to read."""
        context_string = (
            f"### PAST ROUND SUMMARIES  ###\n"
            f"{self.round_summaries}\n\n"
            f"### PAST {self.full_rounds_text_amount} ROUNDS  ###\n"
            f"{self.history_text()}\n\n"
            f"### CURRENT ROUND DIALOGUE ###\n"
            f"{self.currentRound}"
        )
        #print(f"XXX: {context_string} \n YYY" )
        return context_string 
        
    
    def remove_agent_state(self, agent_name: str):
        """Cleans up the dictionaries when an agent dies."""
        self.agent_names.remove(agent_name)
        self.agent_scores.pop(agent_name, None)
        self.agent_forms.pop(agent_name, None)
        self.agent_response_allowed.pop(agent_name, None)

    def add_agent_state(self, agent_name: str, form: str, initial_score: int = None):
        """Initializes dictionaries for a newly born agent."""
        self.agent_names.append(agent_name)
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
            is_allowed = self.agent_response_allowed.get(agent, True)
            status = "\033[92m🟢 SPEAKING\033[0m" if is_allowed else "\033[91m🔴 SILENCED\033[0m"
            
            print(f"{rank:<6} {prefix} {agent:<13} {score:>5}  {status}")
            #print(f"      \033[3m{self.agent_forms.get(agent, 'Unknown form')}\033[0m")
            
        print("="*45 + "\n")
    
    def append_agent_points(self, agent_name, points):
        self.agent_scores[agent_name] += points
        
    def updateFromJudgement(self, judge_result):
        if judge_result.scores:
            for entry in judge_result.scores:
                if entry.name in self.agent_scores:
                    print(entry)
                    self.agent_scores[entry.name] += entry.score # USE += HERE
                else:
                    print(f"⚠️ Unknown player: {entry.name}")

        # 2. Update Forms and Status (Direct Assignment)
        if judge_result.forms:
            for entry in judge_result.forms:
                self.agent_forms[entry.name] = entry.update_value
        
        if judge_result.agent_response_allowed:
            for entry in judge_result.agent_response_allowed:
                self.agent_response_allowed[entry.name] = entry.update_value
                
    def resetScores(self):
        for entry in self.agent_scores:
            self.agent_scores[entry] = 0
                
        