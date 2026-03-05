#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from core.bootstrap import create_engine
from core.sinks.console_sink import ConsoleGameEventSink
from core.sinks.recording_sink import RecordingGameEventSink


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a live simulation and record all sink events to JSONL for TUI replay."
    )
    parser.add_argument("--players", type=int, default=5, help="Number of players (default: 5)")
    parser.add_argument(
        "--generic-players",
        action="store_true",
        default=True,
        help="Use generic players (default: true)",
    )
    parser.add_argument(
        "--no-generic-players",
        action="store_false",
        dest="generic_players",
        help="Use generated balanced cast instead of generic players.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL path (default: output/replays/replay-<timestamp>.jsonl)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print live console output while recording.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    default_name = f"replay-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    output_path = Path(args.output) if args.output else Path("output/replays") / default_name

    delegate = None if args.quiet else ConsoleGameEventSink()

    created_sinks: list[RecordingGameEventSink] = []

    def sink_factory() -> RecordingGameEventSink:
        sink = RecordingGameEventSink(str(output_path), delegate=delegate)
        created_sinks.append(sink)
        return sink

    engine = create_engine(game_sink_class=sink_factory)
    try:
        engine.run(number_of_players=args.players, generic_players=args.generic_players)
    finally:
        for sink in created_sinks:
            sink.close()

    print(f"\nReplay written to: {output_path}")
    print(f"Replay in TUI: uv run python3 tui_replay.py --input {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
