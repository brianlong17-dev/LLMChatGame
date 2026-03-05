#!/usr/bin/env bash
set -euo pipefail

# One-command live flow:
# 1) Open TUI replay in a new Terminal window (follow mode)
# 2) Start a live game in current terminal and record into the same file
#
# Usage:
#   scripts/start_live_tui_game.sh
#   scripts/start_live_tui_game.sh --players 6
#   scripts/start_live_tui_game.sh --players 6 --no-generic-players
#   scripts/start_live_tui_game.sh --output output/replays/my-live.jsonl
#   scripts/start_live_tui_game.sh --no-popout --players 6

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

OUTPUT_PATH=""
NO_POPOUT=0
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-popout)
      NO_POPOUT=1
      shift
      ;;
    --output)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --output" >&2
        exit 2
      fi
      OUTPUT_PATH="$2"
      ARGS+=("$1" "$2")
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$OUTPUT_PATH" ]]; then
  timestamp="$(date +%Y%m%d-%H%M%S)"
  OUTPUT_PATH="output/replays/replay-${timestamp}.jsonl"
  ARGS+=("--output" "$OUTPUT_PATH")
fi

mkdir -p "$(dirname "$ROOT_DIR/$OUTPUT_PATH")"
touch "$ROOT_DIR/$OUTPUT_PATH"

if [[ "$NO_POPOUT" -eq 0 ]]; then
  echo "Opening live replay UI in new Terminal window..."
  "$ROOT_DIR/scripts/launch_tui_replay_terminal.sh" "$OUTPUT_PATH" --follow --refresh-ms 500
  # Give Terminal a moment to open before game output starts.
  sleep 0.4
else
  echo "Popout disabled (--no-popout)."
  echo "Run this in another terminal to follow live:"
  echo "  cd \"$ROOT_DIR\" && uv run python3 tui_replay.py --input \"$OUTPUT_PATH\" --follow --refresh-ms 500"
fi

echo "Starting live game. Recording to: $OUTPUT_PATH"
cd "$ROOT_DIR"
uv run python3 run_and_record.py "${ARGS[@]}"

echo "\nLive replay file: $OUTPUT_PATH"
