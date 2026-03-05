#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from core.tui.app import ReplayTUI
from core.tui.events import EventParseError, load_raw_events, normalize_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay game events in a local CRT-style terminal UI."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a replay file (.jsonl or .json)",
    )
    parser.add_argument(
        "--autoplay",
        action="store_true",
        help="Start with autoplay enabled.",
    )
    parser.add_argument(
        "--phase-delay-ms",
        type=int,
        default=1800,
        help="Autoplay delay between phases in milliseconds (default: 1800).",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Follow the replay file for live updates while it is being written.",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=1200,
        help="Refresh interval while following (milliseconds, default: 1200).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        raw_events = load_raw_events(args.input)
        events = normalize_events(raw_events)
    except EventParseError as exc:
        if args.follow and "No events found in JSONL file" in str(exc):
            events = []
        else:
            print(f"Input error: {exc}", file=sys.stderr)
            return 2

    app = ReplayTUI(
        events=events,
        autoplay=args.autoplay,
        phase_delay_ms=max(100, args.phase_delay_ms),
        follow_file=args.input if args.follow else None,
        follow_refresh_ms=max(250, args.refresh_ms),
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
