from abc import ABC, abstractmethod
from typing import Union

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

    def output_tutorial_message(self, message: str, hold: bool = True, next_level: str | None = None) -> None:
        """Scripted tutorial line for human players. For now: a public host message.
        hold=False renders it complete without gating the feed on a NEXT press.
        next_level is a level id; the web client turns the NEXT press into a jump
        back to the lobby with that level preselected."""
        self.on_public_action("HOST", message, animate_as_player=False, should_hold=False)

    @abstractmethod
    def on_linebreak(self) -> None:
        """Structural separator in the feed. On console: a blank line/divider."""
        ...

    @abstractmethod
    def on_game_over(self, winner_names: list[str]) -> None:
        """Final survivor(s) declared. Fired once at the end."""
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
    def on_phase_rounds(self, rounds: list[str]) -> None:
        """List of round display names for the current phase, in order."""
        ...

    @abstractmethod
    def on_phase_round_index(self, index: int) -> None:
        """Current round index within the phase (0-based)."""
        ...

    @abstractmethod
    def on_round_start(self, round_number: int, round_type: str, round_name: str, scores: str) -> None:
        """Signals a new round beginning, with its type, display name, and current scores."""
        ...

    @abstractmethod
    def on_round_summary(self, summary: str) -> None:
        """Game master's summary of the round just completed."""
        ...

    # -- Speech and thought ---------------------------------------------------

    @abstractmethod
    def on_public_action(self, speaker: Speaker, message: str, color: str = "",
                         animate_as_player: bool = True, should_hold: bool = True, directed_to_name=None,
                         is_reply: bool = False, is_human: bool = False, pop_wrap: bool = False, widget: dict | None = None) -> None:
        """
        A speaker acted publicly — goes into game history, visible to all agents.
        color is a hint for terminal renderers; animate_as_player signals whether the
        frontend should word-by-word animate this message like a player (True for players
        and generated host lines; False for scripted host → HostStagger, and SYSTEM/humans).
        should_hold signals whether the frontend should pause queue draining until the
        viewer presses next (False for HOST, SYSTEM, human players, back-to-back host).
        is_reply marks this message as a threaded reply (frontend emits child: true).
        widget, if given, is a widget-state snapshot that should apply at the exact
        moment this message clears should_hold/animation gating, instead of as an
        independently-ordered on_widget_update event (avoids the widget updating
        ahead of a reveal the viewer hasn't advanced to yet).
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
    def system_private(self, message: str, border_bottom: bool = False) -> None:
        """System-only private output that should never enter public history."""
        ...

    @abstractmethod
    def system_public(self, message: str, border_bottom: bool = False) -> None:
        """System output that is part of the public game record."""
        ...

    @abstractmethod
    def on_warning(self, message: str) -> None:
        """Non-fatal warning, e.g. missing state."""
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
    def on_evictions_update(self, evicted_names: list[str]) -> None:
        """List of evicted players updated."""
        ...

    @abstractmethod
    def on_private_conversation(self, entry) -> None:
        """A private conversation between specific players."""
        ...

    def on_cast(self, names: list[str]) -> None:
        """Announce the full player roster once the game's agents are finalized. No-op by default."""
        pass

    def on_segment_titles(self, titles: list[str]) -> None:
        """Send the predetermined list of segment names for the current round. No-op by default."""
        pass

    def on_feed_marker(self, label: str) -> None:
        """Drop an invisible anchor in the feed at the start of a named segment. No-op by default."""
        pass

    def on_widget_update(self, widget: dict | None) -> None:
        """Push a full widget state snapshot to the sidebar. No-op by default."""
        pass

    def update_is_typing(self, typing_names: list[str]) -> None:
        """Names of agents currently mid-turn. No-op by default."""
        pass

    def add_summary_commentary_for_phase(self, agent_name: str, commentary: str, phase_number: int) -> None:
        """An agent's private end-of-phase commentary line. No-op by default."""
        pass

    def wait_for_continue_next_round(self) -> None:
        pass

    def _request_continue_next_round(self) -> None:
        pass

    def loading_string(self, message: str) -> None:
        """Display an animated loading message in the feed. No-op by default."""
        pass

    def end_loading(self, message: str = None) -> None:
        """Remove the loading message from the feed. If `message` is given, the
        loading row stays in place showing that text (no dots); otherwise it
        becomes an invisible placeholder that preserves layout. No-op by default."""
        pass

    @abstractmethod
    def get_user_input_form(self, form) -> dict:
        """Collect a whole turn's worth of input for a human-controlled player."""
        ...


# ---------------------------------------------------------------------------
# Console implementation
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class NoopGameSink(GameEventSink):
    """Silently discards all events. Use in tests that don't care about output."""

    def get_user_input_form(self, form):
        raise RuntimeError("NoopGameSink cannot collect user input")

    def on_game_intro(self, message): pass
    def on_linebreak(self): pass
    def on_game_over(self, winner_names): pass
    def on_phase_header(self, phase_number): pass
    def on_phase_intro(self, host_text, summary_text): pass
    def on_phase_rounds(self, rounds): pass
    def on_phase_round_index(self, index): pass
    def on_round_start(self, round_number, round_type, round_name, scores): pass
    def on_round_summary(self, summary): pass
    def on_public_action(self, speaker, message, color="", animate_as_player=True, should_hold=True, directed_to_name=None, is_reply=False, is_human=False, pop_wrap=False, widget=None): pass
    def on_private_thought(self, speaker, message): pass
    def system_private(self, message, border_bottom=False): pass
    def system_public(self, message, border_bottom=False): pass
    def on_warning(self, message): pass
    def delay(self, delay): pass
    def on_points_update(self, points): pass
    def on_evictions_update(self, evicted_names): pass
    def on_private_conversation(self, entry): pass
    def on_widget_update(self, widget): pass

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
        self.game_overs: list[list[str]] = []
        self.phase_headers: list[int] = []
        self.phase_intros: list[dict] = []
        self.round_starts: list[dict] = []
        self.round_summaries: list[str] = []
        self.public_actions: list[dict] = []
        self.private_thoughts: list[dict] = []
        self.system_messages: list[dict] = []
        self.points_updates: list[dict[str, int]] = []
        self.evictions_updates: list[str] = []
        self.widget_updates: list = []
        

    def get_user_input_form(self, form):
        raise RuntimeError("CapturingGameSink cannot collect user input")

    def on_game_intro(self, message):
        self.game_intros.append(message)

    def on_linebreak(self): pass

    def on_game_over(self, winner_names):
        self.game_overs.append(winner_names)

    def on_phase_header(self, phase_number):
        self.phase_headers.append(phase_number)

    def on_phase_intro(self, host_text, summary_text):
        self.phase_intros.append({"host_text": host_text, "summary_text": summary_text})

    def on_phase_rounds(self, rounds): pass
    def on_phase_round_index(self, index): pass

    def on_round_start(self, round_number, round_type, round_name, scores):
        self.round_starts.append({"round_number": round_number, "round_type": round_type, "round_name": round_name, "scores": scores})

    def on_round_summary(self, summary):
        self.round_summaries.append(summary)

    def on_public_action(self, speaker, message, color="", animate_as_player=True, should_hold=True, directed_to_name=None, is_reply=False, is_human=False, pop_wrap=False, widget=None):
        if directed_to_name:
            message = f"@{directed_to_name} - {message}"
        self.public_actions.append({"speaker": speaker, "message": message, "color": color})

    def on_private_thought(self, speaker, message):
        self.private_thoughts.append({"speaker": speaker, "message": message})

    def system_private(self, message, border_bottom=False):
        self.system_messages.append({"message": message})

    def system_public(self, message, border_bottom=False):
        self.system_messages.append({"message": message})

    def on_warning(self, message):
        self.system_messages.append({"message": f"WARNING: {message}"})
        
    def delay(self, delay: float = 0.0) -> None:
        pass

    def on_points_update(self, points: dict[str, int]) -> None:
        self.points_updates.append(dict(points))
        
    def on_evictions_update(self, eviction_names: list[str]) -> None:
        self.evictions_updates.append(list(eviction_names))

    def on_private_conversation(self, entry) -> None:
        pass

    def on_widget_update(self, widget) -> None:
        self.widget_updates.append(widget)

