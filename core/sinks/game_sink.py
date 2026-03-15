from abc import ABC, abstractmethod
from typing import Iterable, Union

from agents.base_agent import BaseAgent

Speaker = Union[BaseAgent, str]


class GameEventSink(ABC):
    """
    Abstract contract for all game output.

    GameBoard and SimulationEngine fire events here — implementations decide
    what to do with them. Today: terminal. Future: websocket, replay recorder, etc.

    Speaker args accept either a BaseAgent or a plain string ("SYSTEM", "HOST", "").
    Each implementation resolves what it needs (.name, .color, etc.) itself.
    """

    # -- Game lifecycle -------------------------------------------------------

    @abstractmethod
    def on_game_intro(self, message: str) -> None:
        """The host's opening monologue. Fired once at the very start."""
        ...

    @abstractmethod
    def on_game_over(self, winner_name: str) -> None:
        """Final survivor declared. Fired once at the end."""
        ...

    # -- Phase lifecycle ------------------------------------------------------

    @abstractmethod
    def on_phase_header(self, phase_number: int) -> None:
        """
        Structural marker that a new phase is beginning.
        On console: line breaks + phase number.
        On a frontend: could drive a full-screen transition.
        """
        ...

    @abstractmethod
    def on_phase_intro(self, host_text: str, summary_text: str) -> None:
        """
        Two distinct pieces: host flavour text and the mechanical
        summary of what's about to happen this phase.
        """
        ...

    # -- Round lifecycle ------------------------------------------------------

    @abstractmethod
    def on_round_start(self, round_number: int, scores: str) -> None:
        """
        Signals a new round beginning. Scores are bundled here because
        on console they always print together, and on a frontend this
        is the moment the scoreboard widget refreshes.
        """
        ...

    @abstractmethod
    def on_round_summary(self, summary: str) -> None:
        """Game master's summary of the round just completed."""
        ...

    @abstractmethod
    def on_turn_header(self, turn_number: int) -> None:
        """Visual separator between individual turns within a round."""
        ...

    # -- Speech and thought ---------------------------------------------------

    @abstractmethod
    def on_public_action(self, speaker: Speaker, message: str, color: str = "") -> None:
        """
        A speaker acted publicly — goes into game history, visible to all agents.
        color is a hint for terminal renderers; other sinks can ignore it.
        """
        ...

    @abstractmethod
    def on_private_thought(self, speaker: Speaker, message: str) -> None:
        """
        Internal monologue — not part of game history, display only.
        On a frontend this might be a collapsed/hoverable aside.
        """
        ...

    @abstractmethod
    def on_inner_workings(
        self,
        speaker: Speaker,
        inner_workings: Iterable[tuple[str, object]],
        override: bool = False,
    ) -> None:
        """
        Optional structured debug output derived from non-public response fields.
        Implementations can ignore it unless override is enabled.
        """
        ...

    @abstractmethod
    def system_private(self, speaker: Speaker, message: str) -> None:
        """System-only private output that should never enter public history."""
        ...

    @abstractmethod
    def delay(self, delay: float = 0.0) -> None:
        """ 
        will probably move, but.. we need to stagger the resonses slightly 
        when they're thread pooling.
        """
        
    @abstractmethod
    def on_points_update(self, points: dict[str, int]) -> None:
        """Scoreboard changed outside of round boundaries."""
        ...

    @abstractmethod
    def get_user_input_simple(self, field_name: str, description: str) -> str:
        """Collect freeform input for a human-controlled player."""
        ...

    @abstractmethod
    def get_user_input_multiple_choice(
        self,
        field_name: str,
        description: str,
        choices: list[str],
    ) -> str:
        """Collect a single choice for a human-controlled player."""
        ...


# ---------------------------------------------------------------------------
# Console implementation
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class NoopGameSink(GameEventSink):
    """Silently discards all events. Use in tests that don't care about output."""

    def get_user_input_simple(self, field_name, description):
        raise RuntimeError("NoopGameSink cannot collect user input")

    def get_user_input_multiple_choice(self, field_name, description, choices):
        raise RuntimeError("NoopGameSink cannot collect user input")

    def on_game_intro(self, message): pass
    def on_game_over(self, winner_name): pass
    def on_phase_header(self, phase_number): pass
    def on_phase_intro(self, host_text, summary_text): pass
    def on_round_start(self, round_number, scores): pass
    def on_round_summary(self, summary): pass
    def on_turn_header(self, turn_number): pass
    def on_public_action(self, speaker, message, color=""): pass
    def on_private_thought(self, speaker, message): pass
    def on_inner_workings(self, speaker, inner_workings, override=False): pass
    def system_private(self, speaker, message): pass
    def delay(self, delay): pass
    def on_points_update(self, points): pass

class CapturingGameSink(GameEventSink):
    """
    Stores all events for inspection in tests.

    Usage:
        sink = CapturingGameSink()
        board = GameBoard(game_master, sink=sink)
        ...
        assert any("Alice" in str(e["speaker"]) for e in sink.public_actions)
        assert "Alice: 5" in sink.round_starts[0]["scores"]
    """

    def __init__(self):
        self.game_intros: list[str] = []
        self.game_overs: list[str] = []
        self.phase_headers: list[int] = []
        self.phase_intros: list[dict] = []
        self.round_starts: list[dict] = []
        self.round_summaries: list[str] = []
        self.turn_headers: list[int] = []
        self.public_actions: list[dict] = []
        self.private_thoughts: list[dict] = []
        self.system_messages: list[dict] = []
        self.inner_workings: list[dict] = []
        self.points_updates: list[dict[str, int]] = []

    def get_user_input_simple(self, field_name, description):
        raise RuntimeError("CapturingGameSink cannot collect user input")

    def get_user_input_multiple_choice(self, field_name, description, choices):
        raise RuntimeError("CapturingGameSink cannot collect user input")

    def on_game_intro(self, message):
        self.game_intros.append(message)

    def on_game_over(self, winner_name):
        self.game_overs.append(winner_name)

    def on_phase_header(self, phase_number):
        self.phase_headers.append(phase_number)

    def on_phase_intro(self, host_text, summary_text):
        self.phase_intros.append({"host_text": host_text, "summary_text": summary_text})

    def on_round_start(self, round_number, scores):
        self.round_starts.append({"round_number": round_number, "scores": scores})

    def on_round_summary(self, summary):
        self.round_summaries.append(summary)

    def on_turn_header(self, turn_number):
        self.turn_headers.append(turn_number)

    def on_public_action(self, speaker, message, color=""):
        self.public_actions.append({"speaker": speaker, "message": message, "color": color})

    def on_private_thought(self, speaker, message):
        self.private_thoughts.append({"speaker": speaker, "message": message})

    def on_inner_workings(self, speaker, inner_workings, override=False):
        self.inner_workings.append(
            {
                "speaker": speaker,
                "inner_workings": list(inner_workings),
                "override": override,
            }
        )

    def system_private(self, speaker, message):
        self.system_messages.append({"speaker": speaker, "message": message})
        
    def delay(self, delay: float = 0.0) -> None:
        pass

    def on_points_update(self, points: dict[str, int]) -> None:
        self.points_updates.append(dict(points))
