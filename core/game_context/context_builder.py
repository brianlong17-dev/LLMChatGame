from typing import TYPE_CHECKING
from core.game_context.dashboard import Dashboard
from core.models import RoundEntry

if TYPE_CHECKING:
    from core.gameboard import GameBoard
    from core.game_context.game_log import GameLog
    from agents.base_agent import BaseAgent



class ContextBuilder:

    def __init__(self, game_board: 'GameBoard', game_log: 'GameLog'):
        self.game_board = game_board
        self.game_log = game_log
        self.min_rounds_for_context = 0 #for 2.5, they can't handle the excessive context.
        #some settings can probably move here

    def current_round_formatted(self, agent: 'BaseAgent', anchor = None, other_player_message_found = False):
        current_round = self.game_log.current_round

        if self.game_log._current_round_summarisation:
            round_to_format = self._round_after_id(current_round,
                            self.game_log._current_round_summarisation_until)
            return self.game_log._current_round_summarisation + self._formatted_round(round_to_format, agent, anchor, other_player_message_found)
        else:
            return self._formatted_round(self.game_log.current_round, agent, anchor, other_player_message_found)
        

    def _round_after_id(self, round, message_id):
        round_messages = []
        for message in round.messageEntries:
            if message.id > message_id:
                round_messages.append(message)
        return RoundEntry(phase_number=round.phase_number, round_number=round.round_number, messageEntries=round_messages)

    def _previous_round_entries_for_context(self):
        rounds = self.game_log.completed_phase_rounds(self.game_board.phase_number)
        if len(rounds) < self.min_rounds_for_context:
            #will never reach here if 0
            rounds = self.game_log.completed_round_entries[-self.min_rounds_for_context:]
        return rounds
        
    def previous_rounds_formatted(self, agent: 'BaseAgent', anchor, other_player_message_found):
        rounds = self._previous_round_entries_for_context()
        if len(rounds) == 0:
            return ""
        else:
            rounds_string = f"=== PAST {len(rounds)} ROUNDS  ===\n"
            rounds_string += "\n\n".join(self._formatted_round(r, agent, anchor, other_player_message_found) for r in rounds)
        return rounds_string
    
    def phase_rounds_string(self, agent: 'BaseAgent'):  # Used to make a phase to summarise
        return self._formatted_phase(self.game_board.phase_number, agent)

    def _formatted_phase(self, phase_number, agent):
        rounds = self.game_log.completed_phase_rounds(phase_number)
        if len(rounds) == 0:
            return "This is the first round. There is no prior history."

        history_blocks = []
        for i, round in enumerate(rounds):
            block = (
                f"{self._round_header(round)}\n"
                f"{self._formatted_round(round, agent)}"
            )
            history_blocks.append(block)
        return "\n\n".join(history_blocks)

    def _round_header(self, round):
        return f"--- Phase: {round.phase_number}, Round: {round.round_number} ---"

    def _recency_anchor(self, agent):
        if agent.name in self.game_board.RESERVED_NAMES:
            return None, False
        if self.game_log._current_round_summarisation:
            rounds = [self._round_after_id(self.game_log.current_round,
                                           self.game_log._current_round_summarisation_until)]
        else:
            rounds = [self.game_log.current_round] + self._previous_round_entries_for_context()
            
        other_player_message_found = False
        
        for round in rounds:
            for entry in reversed(round.messageEntries):
                for message in reversed(entry.messages):
                    if message["speaker"] == agent.name:
                        if entry.visibility_restriction is not None:
                            #if they're in a private convo, anchor not relevent
                            return None, False 
                        else:
                            return message, other_player_message_found
                    if message["speaker"] not in self.game_board.RESERVED_NAMES:
                        other_player_message_found = True
                    
        return None, False  
    
    def _formatted_round(self, round: 'RoundEntry', agent: 'BaseAgent', anchor = None, other_player_message_found = False):

        output = f"\n{self._round_header(round)}\n"
        if len(round.messageEntries) == 0:
            return output + "No messages yet for round."

        if other_player_message_found:
            anchor_message = "\n===[This was your last message — react to what's happened since. Don't repeat above message. ]==="
        else:
            anchor_message = "\n===[ This was your last message — it's already been said. Your turn now is a fresh action, not a reaction. Don't repeat or recap the above; respond only to what the host has just asked. ]==="
            
        for entry in round.messageEntries:
            if entry.visibility_restriction is None:
                for message in entry.messages:
                    
                    output += (f"\n{message['speaker']}: {message['message']}")
                    if message is anchor:
                        #TODO - this check should be more solid
                        output += anchor_message
                    
            else:
                if agent.name in entry.visibility_restriction:
                    if self.game_board.SYS_ADMIN in entry.visibility_restriction:
                        #We dont need the tags for a sys_admin message
                        for message in entry.messages:
                            output += f"\n [Private System Message] {message['message']} [End Private Message]"
                    else:
                        names = ", ".join(entry.visibility_restriction)
                        output += f"\n=== Private Conversation between {names} ===\n"
                        for message in entry.messages:
                            output += (f"\n{message['speaker']}: {message['message']}")
                        if entry.closed:
                            output += f"\n=== END OF Private Conversation between {names} ===\n"
        return output

    def get_dashboard_string(self, agent: 'BaseAgent') -> str:
        return Dashboard.render(agent, self.game_board)
       