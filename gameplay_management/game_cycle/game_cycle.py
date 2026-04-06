import random
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class CycleRound(BaseRound):

    
    FULL_CONTEXT_CYCLES = 4
    USE_CONTEXT_COMPRESSION = False
    USE_OPTIONAL_RESPONSE = False
    BUFFER_AMOUNT = 0.6
    
    @classmethod
    def is_game(cls):
        return True
    
    def _cycle_game_setup(self):
        self.gameBoard.optional_responses_in_use = self.USE_OPTIONAL_RESPONSE
        if self.USE_CONTEXT_COMPRESSION:
            self._buffer_amount = self.BUFFER_AMOUNT
            self._message_unsumarised_after = self.gameBoard.most_recent_message_id()
            self.summaries: list[tuple[str, int]] = []
        
    def _compress_round(self):
        message_to_summarise = self.gameBoard.messages_since(self._message_unsumarised_after)
        context = self.gameBoard._current_round_messages_up_to(self._message_unsumarised_after)
        summary = self._generate_summary(context, message_to_summarise) 
        self._message_unsumarised_after = self.gameBoard.most_recent_message_id()
        self.summaries.append((summary, self._message_unsumarised_after))
        self._push_game_summaries()
            
        
    def _cycle_game_teardown(self):
        self.gameBoard.optional_responses_in_use = False
    
    @property
    def optional_responses_in_use(self):
        return self.gameBoard.optional_responses_in_use
    
                
    def _format_messages(self, messages):
        lines = []
        for entry in messages:
            for msg in entry.messages:
                lines.append(f"{msg['speaker']}: {msg['message']}")
        return "\n".join(lines)

    def _generate_summary(self, context, message_to_summarise):
        context_str = self._format_messages(context)
        game_text_str = self._format_messages(message_to_summarise)
        return self.simulationEngine.game_master.summarise_game_text(context_str, game_text_str)
              
    def _push_game_summaries(self):
        full_context_cycles = self.FULL_CONTEXT_CYCLES
        summaries_to_push_num = len(self.summaries) - full_context_cycles
        if summaries_to_push_num < 1:
            return
        
        summaries_to_push = self.summaries[:summaries_to_push_num]
        summaries_str = self.format_summaries(summaries_to_push)
        self.gameBoard.push_current_round_summarisation(summaries_str, summaries_to_push[-1][1])
        
    def format_summaries(self, summary_selection):
        string = ""
        for i, (summary_str, _) in enumerate(summary_selection):
            string += f"Cycle {i + 1} summary: {summary_str}\n"
        return string
    
    
