from collections import deque
from core.models import MessageEntry, RoundEntry


SYS_ADMIN = "SYS_ADMIN"


class GameLog:
    def __init__(self):
        self.message_id = 0
        self.current_round: RoundEntry = None
        self.completed_round_entries: list[RoundEntry] = []
        self._current_round_summarisation: str = ""
        self._current_round_summarisation_until: int = None

    def most_recent_message_id(self) -> int:
        return self.message_id

    def push_current_round_summarisation(self, summary: str, last_message_id: int):
        self._current_round_summarisation = summary
        self._current_round_summarisation_until = last_message_id

    def _is_sys_admin_message(self, message: MessageEntry) -> bool:
        return bool(message.visibility_restriction and SYS_ADMIN in message.visibility_restriction)

    def messages_since(self, message_id: int) -> list[MessageEntry]:
        return [m for m in self.current_round.messageEntries if m.id > message_id and not self._is_sys_admin_message(m)]

    def _current_round_messages_up_to(self, message_id: int) -> list[MessageEntry]:
                return [m for m in self.current_round.messageEntries if m.id <= message_id and not self._is_sys_admin_message(m)]

    def _current_round_most_recent_player_entry(self, reserved_names):
        for entry in reversed(self.current_round.messageEntries):
            if len(entry.messages) == 1 and entry.messages[0]['speaker'] not in reserved_names:
                return entry
        return None


    def _current_round_most_recent_message_entry(self):
        entries = [
            entry for entry in self.current_round.messageEntries 
            if entry.visibility_restriction is None
        ] # we dont care about pvt messages
        return entries[-1] if entries else None

    def _is_host_message(self, message_entry, host_name: str) -> bool:
        if not message_entry.messages or len(message_entry.messages) != 1:
            return False
        return message_entry.messages[0]['speaker'] == host_name

    def _get_conversation_entry(self, conversation_id) -> MessageEntry | None:
        return next((e for e in self.current_round.messageEntries if e.id == conversation_id), None)

    def _update_history(self, player_name: str, message: str, visibility_restriction=None) -> int:
        self.message_id += 1
        entry = MessageEntry(
            messages=[{"speaker": player_name, "message": message}],
            id=self.message_id,
            visibility_restriction=visibility_restriction
        )
        self.current_round.messageEntries.append(entry)
        return self.message_id

    def completed_phase_rounds(self, phase_number: int) -> list[RoundEntry]:
        return [r for r in self.completed_round_entries if r.phase_number == phase_number]

    def start_round(self, phase_number: int, round_number: int):
        self._current_round_summarisation = ""
        self._current_round_summarisation_until = None
        self.current_round = RoundEntry(phase_number=phase_number, round_number=round_number, messageEntries=[])

    def close_round(self):
        self.completed_round_entries.append(self.current_round)
