import time

from core.console_renderer import ConsoleRenderer
from core.sinks.game_sink import GameEventSink, Speaker


class ConsoleGameEventSink(GameEventSink):
    """
    Routes all game events to the terminal via ConsoleRenderer.
    Default sink for live runs.
    """

    def on_game_intro(self, message: str) -> None:
        ConsoleRenderer.print_public_action("HOST", message)

    def on_game_over(self, winner_name: str) -> None:
        ConsoleRenderer.print_system_private(f"🏆 FINAL SURVIVOR: {winner_name}")

    def on_phase_header(self, phase_number: int) -> None:
        from prompts.prompts import PromptLibrary
        ConsoleRenderer.print_system_private(PromptLibrary.line_break)
        ConsoleRenderer.print_system_private(f"PHASE: {phase_number}")
        ConsoleRenderer.print_system_private(PromptLibrary.line_break)

    def on_phase_intro(self, host_text: str, summary_text: str) -> None:
        ConsoleRenderer.print_public_action("HOST", host_text)
        ConsoleRenderer.print_public_action("", summary_text, "SYS")
        
    def on_round_end(self, round_number: int, scores: dict[str, int]) -> None:
        #summary should be here.
        pass
    
    
    def on_round_start(self, round_number: int, scores: dict[str, int]) -> None:
        if True:
            input("Press Enter to continue to the next round...")
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        lines = [f"\n{'='*30}", f"{'RANK':<6} {'AGENT':<15} {'SCORE':>5}", "-" * 30]
        for rank, (name, score) in enumerate(sorted_scores, 1):
            prefix = "👑" if rank == 1 else "  "
            lines.append(f"{rank:<6} {prefix} {name:<13} {score:>5}")
        lines.append("=" * 45)
        ConsoleRenderer.print_system_private("\n".join(lines))
        ConsoleRenderer.print_public_action("SYSTEM", f"BEGIN ROUND {round_number}")

    def on_round_summary(self, summary: str) -> None:
        #big question, should this be public? the round summaries should be passed to each agent anyway...
        ConsoleRenderer.print_private("SUMMARY", f"{summary}\n", color_name="YELLOW")

    def on_turn_header(self, turn_number: int) -> None:
        ConsoleRenderer.print_turn_header(turn_number)

    def on_public_action(self, speaker: Speaker, message: str, color: str = "") -> None:
        ConsoleRenderer.print_public_action(speaker, message, color)

    def on_private_thought(self, speaker: Speaker, message: str) -> None:
        ConsoleRenderer.print_private(speaker, message, print_name=False)
        
    def on_inner_workings(self, speaker: Speaker, inner_workings: dict[str: str], override: bool = False) -> None:
        if override: #or setting
            for key, value in inner_workings:
                formatted_key = key.replace('_', ' ').title() 
                message = f"{formatted_key} : {value}"
                self.on_private_thought(speaker, message)
        

    def delay(self, delay: float = 0.0) -> None:
        time.sleep(delay)
        
    def on_points_update(self, points: dict[str, int]) -> None:
        pass
