from dataclasses import dataclass


@dataclass
class MessageEntry:
    messages: list[dict]  # [{"speaker": name, "message": text}]
    id: int #sequential number, allow you to append / access specific convos
    visibility_restriction: set[str] | None = None  # None = public

@dataclass
class RoundEntry:
    phase_number: int
    round_number: int
    messages: list[MessageEntry]
