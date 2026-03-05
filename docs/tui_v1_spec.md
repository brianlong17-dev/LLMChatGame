# TUI V1 Spec

## Goal
Build a local-first terminal UI (TUI) as a step up from line-by-line console printing, while keeping a reusable event model for later web migration.

## Runtime
- Python 3.13+
- `textual` for terminal UI
- Input log formats: `.jsonl` (preferred) and `.json` (array of events)

## Generating Replay Logs
- Run a live game and record replay events:
  - `uv run python3 run_and_record.py`
- Replay in TUI:
  - `uv run python3 tui_replay.py --input output/replays/<replay-file>.jsonl`
- Follow live updates while a replay file is still being written:
  - `uv run python3 tui_replay.py --input output/replays/<replay-file>.jsonl --follow`

## Default Theme
- Primary: phosphor green
- Secondary: dim green
- Summary/host accent: amber
- Alerts/eliminations: dim red
- Overall visual: near-black background with restrained, CRT-like styling

## Screen Regions
- Top status bar: phase position, visibility mode, autoplay state
- Main feed pane (left): one phase page at a time
- Player panel (right): `ACTIVE` and `ELIMINATED`
- Bottom controls bar: key hints

## Visibility Modes
- `Public only` (default): host/public/summary/headers
- `+ Thoughts`: adds private thoughts (dim + italic)
- `+ Inner Workings`: adds internal fields (more dim, subordinate)

## Keybindings
- `left` / `h`: previous phase
- `right` / `l` / `space`: next phase
- `1`: public only
- `2`: show thoughts
- `3`: show inner workings
- `a`: toggle autoplay
- `g`: first phase
- `G`: last phase
- `?`: toggle help
- `q`: quit

## Event Schema (Normalized)
Each event is normalized to:
- `type: str` (required)
- `phase: int` (required)
- `round: int | None`
- `turn: int | None`
- `actor: str | None`
- `text: str | None`
- `summary: str | None`
- `scores: dict[str, int] | None`
- `payload: dict` (full original event)

## Supported Event Types
- `on_game_intro`
- `on_phase_header`
- `on_phase_intro`
- `on_round_start`
- `on_round_summary`
- `on_public_action`
- `on_private_thought`
- `on_inner_workings`
- `on_turn_header`
- `on_game_over`

## Phase Model
- Feed is paginated by phase
- One phase is shown at a time
- Back/forward moves phase pages
- Autoplay defaults to OFF
- If autoplay is ON, app advances by phase after delay and stops at final phase

## Acceptance Checklist (V1)
1. TUI runs locally with one command and a log file.
2. Green theme is default.
3. Split layout: feed left, player panel right.
4. Feed is phase-based, not continuous scroll.
5. Phase navigation works at boundaries.
6. Autoplay defaults OFF and toggles ON/OFF.
7. Autoplay advances and stops on last phase.
8. Visibility mode `1` hides thoughts and inner fields.
9. Visibility mode `2` shows private thoughts.
10. Visibility mode `3` shows inner workings too.
11. Player panel shows ranked active players and leader crown.
12. Eliminated list persists and remains visible.
13. All mapped event types render with distinct treatment.
14. Input supports both `.jsonl` and `.json`.
15. Bad input returns clear error output.
