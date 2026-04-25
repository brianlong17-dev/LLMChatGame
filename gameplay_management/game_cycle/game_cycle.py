from gameplay_management.base_manager import BaseRound


class CycleRound(BaseRound):

    @classmethod
    def is_game(cls):
        return True

    def _cycle_game_setup(self):
        cfg = self.cfg()
        self.turn_manager._buffer_amount = cfg.cycle_buffer_amount
        self.turn_manager.optional_responses_in_use = cfg.cycle_use_optional_response
        
        
        self._use_compression = cfg.cycle_use_context_compression
        if self._use_compression:
            self._full_context_cycles = cfg.cycle_full_context_cycles
            self._message_unsumarised_after = self.gameBoard.most_recent_message_id()
            self.summaries: list[tuple[str, int]] = []
        
    def _compress_round(self):
        if not self._use_compression:
            return
        message_to_summarise = self.gameBoard.messages_since(self._message_unsumarised_after)
        context = self.gameBoard._current_round_messages_up_to(self._message_unsumarised_after)
        summary = self._generate_summary(context, message_to_summarise)
        self._message_unsumarised_after = self.gameBoard.most_recent_message_id()
        self.summaries.append((summary, self._message_unsumarised_after))
        self._push_game_summaries()
            
        
    def _cycle_game_teardown(self):
        pass
        #TODO
        #"here we should push the summary - to the game round..."
    
    @property
    def optional_responses_in_use(self):
        return self.turn_manager.optional_responses_in_use
    
                
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
        full_context_cycles = self._full_context_cycles
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
    
    
