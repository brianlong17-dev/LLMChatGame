from collections import deque

class ConsoleRenderer:
    COLORS = {
        "RED": "\033[91m", "GREEN": "\033[92m", "BLUE": "\033[94m",
        "YELLOW": "\033[93m", "SYSTEM": "\033[1;30m", "RESET": "\033[0m"
    }

    @classmethod
    def print_turn_header(cls, turn_number: int):
        print(f"\n\n\033[1m[TURN {turn_number}]\033[0m")

    @classmethod
    def print_public_action(cls, speaker_name: str, message: str, color_name: str = "RESET"):
        color = cls.COLORS.get(color_name.upper(), cls.COLORS["RESET"])
        print(f"{color}\033[1m{speaker_name}\033[0m: {color}{message}{cls.COLORS['RESET']}")

    @classmethod
    def print_private_thought(cls, message: str, speaker_name: str = "", thought_type: str = "Thoughts", color_name: str = "RESET"):
        color = cls.COLORS.get(color_name.upper(), cls.COLORS["RESET"])
        if speaker_name != "":
            speaker_name = f"[{speaker_name}] - "
        print(f"{color}\033[3m{speaker_name}{thought_type} : {message}{cls.COLORS['RESET']}")

    @classmethod
    def print_system(cls, message: str):
        color = cls.COLORS["SYSTEM"]
        print(f"{color}🤖 [SYSTEM]: {message}{cls.COLORS['RESET']}")

class GameBoard:
    COLORS = {
            "RED": "\033[91m",
            "GREEN": "\033[92m",
            "BLUE": "\033[94m",
            "YELLOW": "\033[93m",
            "RESET": "\033[0m"
        }
    
    def __init__(self, game_master):
        self.full_rounds_text_amount = 2
        self.game_master = game_master
        self.agent_names = []
        self.round_number = 0
        self.turn_number = 0
        self.history = []
        self.currentRound = []
        self.round_entries = deque(maxlen=30)
        self.round_summaries = deque(maxlen=5)
        self.agent_scores: dict[str, int] = {}
        self.agent_response_allowed: dict[str, bool] = {}
        self.agent_forms: dict[str, str] = {}
    
        
            
    def newRound(self):
        #This will move to the simulator
        self.print_leaderboard()
        self.round_number += 1
        self.round_entries.append(list(self.currentRound))
        #print(f"SSS: {self.round_entries}")
        #print(f"PPP: {list(self.round_entries)[-2:]}")
        roundSummary = self.game_master.summariseRound(self)
        roundSummaryString = "\n".join([f"{key}: {value}" for key, value in roundSummary])
        self.round_summaries.append(roundSummary)
        ConsoleRenderer.print_private_thought("SUMMARY", f"{roundSummaryString}", color_name = "YELLOW")
        self.currentRound.clear()
        self.broadcast_public_action("SYSTEM", f"BEGIN ROUND {self.round_number}")
    
    def broadcast_public_action(self, player_name: str, message: str, color: str = "RESET"):
        #TODO need to merge this one with the manager one
        self._update_history(player_name, message)
        ConsoleRenderer.print_public_action(player_name, message, color)
        
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
    
               
    def print_and_save(self, player_name, public_message: str, color = "RESET"):
        self.broadcast_public_action(player_name, public_message, color)
        
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
                
        