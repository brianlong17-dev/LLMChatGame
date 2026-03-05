#!/usr/bin/env bash
set -euo pipefail

# Opens a new macOS Terminal window and runs the local TUI replay app.
# Usage:
#   scripts/launch_tui_replay_terminal.sh
#   scripts/launch_tui_replay_terminal.sh data/replays/sample_game_log.jsonl
#   scripts/launch_tui_replay_terminal.sh data/replays/sample_game_log.jsonl --autoplay --phase-delay-ms 1200

if ! command -v osascript >/dev/null 2>&1; then
  echo "This launcher requires macOS (osascript not found)." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_PATH="${1:-data/replays/sample_game_log.jsonl}"
if [[ $# -gt 0 ]]; then
  shift
fi

EXTRA_ARGS="$*"

escape_for_applescript() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

CMD="cd \"$ROOT_DIR\" && uv run python3 tui_replay.py --input \"$INPUT_PATH\""
if [[ -n "$EXTRA_ARGS" ]]; then
  CMD+=" $EXTRA_ARGS"
fi

CMD_ESCAPED="$(escape_for_applescript "$CMD")"

osascript <<APPLESCRIPT
tell application "Terminal"
  activate
  do script "$CMD_ESCAPED"
end tell
APPLESCRIPT
