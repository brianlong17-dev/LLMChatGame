from __future__ import annotations

from typing import Iterable

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key, MouseScrollDown, MouseScrollUp
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import RichLog, Static

from core.tui.events import (
    EventParseError,
    NormalizedEvent,
    events_for_phase,
    load_raw_events,
    normalize_events,
    phase_numbers,
)
from core.tui.state import (
    PUBLIC_ONLY,
    WITH_INNER,
    WITH_THOUGHTS,
    VisibilityMode,
    compute_player_snapshot,
    event_visible,
)


class ReplayTUI(App[None]):
    CSS = """
    Screen {
        background: #050b05;
        color: #7cff7a;
    }

    #root {
        layout: vertical;
        height: 100%;
    }

    #status {
        height: 1;
        padding: 0 1;
        color: #7cff7a;
        background: #0a120a;
        text-style: bold;
    }

    #body {
        height: 1fr;
    }

    #feed {
        width: 72%;
        height: 100%;
        border: solid #2f572d;
        padding: 1;
        overflow-y: auto;
        overflow-x: auto;
    }

    #players {
        width: 28%;
        height: 100%;
        border: solid #2f572d;
        padding: 1;
        overflow-y: auto;
    }

    #controls {
        height: 1;
        color: #4fae4d;
        background: #0a120a;
        padding: 0 1;
    }

    #help {
        dock: bottom;
        width: 100%;
        height: auto;
        background: #0a120a;
        color: #7cff7a;
        border-top: solid #2f572d;
        padding: 1;
        display: none;
    }

    .flicker {
        background: #0f1d0f;
    }
    """

    BINDINGS = [
        ("left,h", "prev_phase", "Prev"),
        ("right,l,space", "next_phase", "Next"),
        ("up,k", "scroll_up", "ScrollUp"),
        ("down,j", "scroll_down", "ScrollDown"),
        ("pageup", "page_up", "PageUp"),
        ("pagedown", "page_down", "PageDown"),
        ("end,f", "follow_latest", "Live"),
        ("a", "toggle_autoplay", "Autoplay"),
        ("1", "mode_public", "Public"),
        ("2", "mode_thoughts", "Thoughts"),
        ("3", "mode_inner", "Inner"),
        ("g", "first_phase", "First"),
        ("shift+g", "last_phase", "Last"),
        ("question_mark", "toggle_help", "Help"),
        ("q", "quit", "Quit"),
    ]

    mode: reactive[VisibilityMode] = reactive(PUBLIC_ONLY)
    current_phase_index: reactive[int] = reactive(0)
    autoplay: reactive[bool] = reactive(False)

    def __init__(
        self,
        events: list[NormalizedEvent],
        default_mode: VisibilityMode = PUBLIC_ONLY,
        autoplay: bool = False,
        phase_delay_ms: int = 1800,
        follow_file: str | None = None,
        follow_refresh_ms: int = 1200,
    ):
        super().__init__()
        self.events = events
        self.phases = phase_numbers(events)
        self._default_mode = default_mode
        self._default_autoplay = autoplay
        self.phase_delay_ms = phase_delay_ms
        self._autoplay_timer: Timer | None = None
        self._paused_after_autoplay_end = False
        self._follow_attached = True
        self.follow_file = follow_file
        self.follow_refresh_ms = max(250, follow_refresh_ms)
        self._follow_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            yield Static(id="status")
            with Horizontal(id="body"):
                yield RichLog(id="feed", auto_scroll=False, markup=True, wrap=True)
                yield Static(id="players")
            yield Static(id="controls")
            yield Static(self._help_text(), id="help")

    def on_mount(self) -> None:
        # Set reactive state after mount to avoid watcher-triggered renders
        # before the screen exists.
        self.mode = self._default_mode
        self.autoplay = False
        if self._default_autoplay:
            self._set_autoplay(True)
        if self.follow_file:
            self._follow_timer = self.set_interval(
                self.follow_refresh_ms / 1000.0,
                self._poll_follow_file,
                pause=False,
            )
        self._render(scroll_to_bottom=False)

    def on_key(self, event: Key) -> None:
        # Keep phase navigation stable regardless of focused widget.
        if event.key == "left":
            self.action_prev_phase()
            event.stop()
            return
        if event.key == "right":
            self.action_next_phase()
            event.stop()
            return

    def watch_current_phase_index(self, _: int) -> None:
        if not self.is_mounted:
            return
        self._render(scroll_to_bottom=False)

    def watch_mode(self, _: VisibilityMode) -> None:
        if not self.is_mounted:
            return
        self._render(scroll_to_bottom=None)

    def watch_autoplay(self, _: bool) -> None:
        if not self.is_mounted:
            return
        self._render(scroll_to_bottom=None)

    def action_prev_phase(self) -> None:
        self._paused_after_autoplay_end = False
        if self.follow_file:
            self._follow_attached = False
        if self.current_phase_index > 0:
            self.current_phase_index -= 1
            self._phase_flicker()

    def action_next_phase(self) -> None:
        self._paused_after_autoplay_end = False
        if self.current_phase_index < len(self.phases) - 1:
            self.current_phase_index += 1
            self._phase_flicker()
        if self.follow_file and self.current_phase_index == len(self.phases) - 1:
            self._follow_attached = self._is_feed_at_bottom()

    def action_first_phase(self) -> None:
        self._paused_after_autoplay_end = False
        if self.follow_file:
            self._follow_attached = False
        self.current_phase_index = 0

    def action_last_phase(self) -> None:
        self._paused_after_autoplay_end = False
        self.current_phase_index = len(self.phases) - 1
        if self.follow_file:
            self._follow_attached = self._is_feed_at_bottom()

    def action_mode_public(self) -> None:
        self.mode = PUBLIC_ONLY

    def action_mode_thoughts(self) -> None:
        self.mode = WITH_THOUGHTS

    def action_mode_inner(self) -> None:
        self.mode = WITH_INNER

    def action_toggle_autoplay(self) -> None:
        self._set_autoplay(not self.autoplay)

    def action_toggle_help(self) -> None:
        help_widget = self.query_one("#help", Static)
        help_widget.display = not help_widget.display

    def action_scroll_up(self) -> None:
        feed = self.query_one("#feed", RichLog)
        feed.scroll_relative(y=-3)
        if self.follow_file:
            self._follow_attached = False

    def action_scroll_down(self) -> None:
        feed = self.query_one("#feed", RichLog)
        feed.scroll_relative(y=3)
        if self.follow_file and self.current_phase_index == len(self.phases) - 1:
            self._follow_attached = self._is_feed_at_bottom()

    def action_page_up(self) -> None:
        feed = self.query_one("#feed", RichLog)
        feed.scroll_page_up()
        if self.follow_file:
            self._follow_attached = False

    def action_page_down(self) -> None:
        feed = self.query_one("#feed", RichLog)
        feed.scroll_page_down()
        if self.follow_file and self.current_phase_index == len(self.phases) - 1:
            self._follow_attached = self._is_feed_at_bottom()

    def action_follow_latest(self) -> None:
        if not self.follow_file:
            return
        self._paused_after_autoplay_end = False
        self._follow_attached = True
        self.current_phase_index = len(self.phases) - 1
        self._render(scroll_to_bottom=True)

    def _set_autoplay(self, enabled: bool) -> None:
        self.autoplay = enabled
        if enabled:
            self._paused_after_autoplay_end = False
        if self._autoplay_timer is not None:
            self._autoplay_timer.stop()
            self._autoplay_timer = None

        if enabled:
            self._autoplay_timer = self.set_interval(
                self.phase_delay_ms / 1000.0,
                self._autoplay_tick,
                pause=False,
            )

    def _autoplay_tick(self) -> None:
        if self.current_phase_index >= len(self.phases) - 1:
            self._set_autoplay(False)
            self._paused_after_autoplay_end = True
            return
        self.action_next_phase()

    def _render(self, scroll_to_bottom: bool | None = None) -> None:
        phase_number = self.phases[self.current_phase_index]
        mode_label = {
            PUBLIC_ONLY: "PUBLIC",
            WITH_THOUGHTS: "THOUGHTS",
            WITH_INNER: "INNER",
        }[self.mode]

        status = self.query_one("#status", Static)
        follow_label = "ON" if self.follow_file else "OFF"
        if self._paused_after_autoplay_end:
            lock_label = "LOCKED"
        elif self.follow_file and not self._follow_attached:
            lock_label = "PAUSED"
        else:
            lock_label = "LIVE"
        status.update(
            f"PHASE {self.current_phase_index + 1}/{len(self.phases)} (#{phase_number})"
            f" | MODE: {mode_label} | AUTOPLAY: {'ON' if self.autoplay else 'OFF'}"
            f" | FOLLOW: {follow_label}/{lock_label}"
        )

        controls = self.query_one("#controls", Static)
        controls.update(
            "[left/right] phase  [up/down,pgup/pgdn] scroll  [f/end] live  [1/2/3] visibility  [a] autoplay  [g/G] ends  [?] help  [q] quit"
        )

        feed = self.query_one("#feed", RichLog)
        prev_scroll_y = feed.scroll_y
        feed.clear()
        for line in self._render_feed(phase_number).splitlines():
            feed.write(line)
        if scroll_to_bottom is True:
            feed.scroll_end(animate=False)
        elif scroll_to_bottom is False:
            feed.scroll_home(animate=False)
        else:
            # Preserve viewport when rerendering for live updates or mode/status changes.
            target_y = min(prev_scroll_y, feed.max_scroll_y)
            feed.scroll_to(y=target_y, animate=False)

        players = self.query_one("#players", Static)
        players.update(self._render_players(phase_number))

    def _render_feed(self, phase_number: int) -> str:
        phase_events = events_for_phase(self.events, phase_number)
        visible_events = [event for event in phase_events if event_visible(event, self.mode)]
        if not visible_events:
            return "[dim]No visible events in this phase for current mode.[/dim]"

        lines: list[str] = []
        for event in visible_events:
            lines.extend(self._format_event(event))
            lines.append("")
        return "\n".join(lines)

    def _render_players(self, phase_number: int) -> str:
        snapshot = compute_player_snapshot(self.events, phase_number)

        lines: list[str] = ["[bold]ACTIVE[/bold]"]
        if snapshot.active_scores:
            ranked = sorted(snapshot.active_scores.items(), key=lambda item: (-item[1], item[0]))
            for index, (name, score) in enumerate(ranked, start=1):
                crown = " 👑" if index == 1 else ""
                lines.append(f"{index:>2}. {escape(name)}  {score}{crown}")
        else:
            lines.append("[dim]No active scoreboard yet[/dim]")

        lines.append("")
        lines.append("[bold]ELIMINATED[/bold]")
        if snapshot.eliminated:
            for name in snapshot.eliminated:
                lines.append(f"[dim][strike]{escape(name)}[/strike][/dim]")
        else:
            lines.append("[dim]None[/dim]")

        return "\n".join(lines)

    def _phase_flicker(self) -> None:
        body = self.query_one("#body", Horizontal)
        body.add_class("flicker")
        self.set_timer(0.08, lambda: body.remove_class("flicker"))

    def _poll_follow_file(self) -> None:
        if not self.follow_file:
            return
        try:
            raw_events = load_raw_events(self.follow_file)
            new_events = normalize_events(raw_events)
        except (OSError, EventParseError):
            return

        if len(new_events) == len(self.events):
            return

        self.events = new_events
        self.phases = phase_numbers(new_events)

        if self._paused_after_autoplay_end:
            self.current_phase_index = min(self.current_phase_index, len(self.phases) - 1)
            self._render(scroll_to_bottom=None)
            return

        if self._follow_attached:
            self.current_phase_index = len(self.phases) - 1
            self._render(scroll_to_bottom=True)
            return

        self.current_phase_index = min(self.current_phase_index, len(self.phases) - 1)
        self._render(scroll_to_bottom=None)

    def _is_feed_at_bottom(self) -> bool:
        feed = self.query_one("#feed", RichLog)
        return feed.scroll_y >= max(0, feed.max_scroll_y - 0.5)

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        if getattr(event.widget, "id", "") == "feed":
            self.action_scroll_up()
            event.stop()

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        if getattr(event.widget, "id", "") == "feed":
            self.action_scroll_down()
            event.stop()

    def _format_event(self, event: NormalizedEvent) -> Iterable[str]:
        message = escape(event.text or "")
        summary = escape(event.summary or "")
        actor = escape(event.actor or "")

        if event.type == "on_game_intro":
            return [f"[bold #7cff7a]=== GAME INTRO ===[/bold #7cff7a]", message]

        if event.type == "on_phase_header":
            phase_label = event.payload.get("phase") or event.payload.get("phase_number") or event.phase
            return [f"[bold #4fae4d]----- PHASE {phase_label} -----[/bold #4fae4d]"]

        if event.type == "on_phase_intro":
            host_line = f"[bold #ffb347]HOST:[/bold #ffb347] {message}"
            if summary:
                return [host_line, f"[dim]{summary}[/dim]"]
            return [host_line]

        if event.type == "on_round_start":
            round_number = event.round if event.round is not None else event.payload.get("round_number", "?")
            return [f"[bold]BEGIN ROUND {round_number}[/bold]"]

        if event.type == "on_round_summary":
            text = summary or message
            return [f"[bold #ffb347]SUMMARY[/bold #ffb347] {text}"]

        if event.type == "on_points_update":
            # Scoreboard is updated from the side panel snapshot; keep feed clean.
            return []

        if event.type == "on_public_action":
            name = actor if actor else "SYSTEM"
            return [f"[bold #7cff7a]{name}:[/bold #7cff7a] {message}"]

        if event.type == "on_private_thought":
            name = actor if actor else "THOUGHT"
            return [f"[italic #4fae4d]{name}: {message}[/italic #4fae4d]"]

        if event.type == "on_inner_workings":
            data = escape(str(event.payload.get("inner") or event.payload.get("details") or event.payload))
            name = actor if actor else "INNER"
            return [f"[dim]{name}: {data}[/dim]"]

        if event.type == "on_turn_header":
            turn_number = event.turn if event.turn is not None else event.payload.get("turn_number", "?")
            return [f"[bold #4fae4d]-- TURN {turn_number} --[/bold #4fae4d]"]

        if event.type == "on_game_over":
            winner = escape(
                str(event.payload.get("winner_name") or event.payload.get("winner") or event.text or "UNKNOWN")
            )
            return [f"[bold #d95c5c]*** FINAL SURVIVOR: {winner} ***[/bold #d95c5c]"]

        return [f"[dim]{escape(event.type)}[/dim] {message or summary}"]

    @staticmethod
    def _help_text() -> str:
        return (
            "Keys\n"
            "  left/h: previous phase\n"
            "  right/l/space: next phase\n"
            "  up/k, down/j: scroll feed\n"
            "  pageup/pagedown: page scroll\n"
            "  f/end: jump to live tail\n"
            "  1/2/3: visibility mode\n"
            "  a: autoplay on/off\n"
            "  g/G: first/last phase\n"
            "  ?: toggle this help\n"
            "  q: quit"
        )
