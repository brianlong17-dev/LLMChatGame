# Future Refactors
- We need to look at printing the action when they do an action- it can be interesting, but also just informative 
- Like an end of phase commentary, or something to read while they do their sumarries.
- Kind of invovles the game host overhaul- we can do it before that , but a phase commentary like a sports commentator, or whatvever.

## Rename Debater → Contestant
- `agents/player.py` → `agents/contestant.py`
- Class `Debater` → `Contestant`
- Update all references: `simulation_engine.py`, `bootstrap.py`, `character_generation/`, `models/player_models.py`, type hints throughout

## TYPE_CHECKING imports throughout
- Move all cross-module type-only imports under `TYPE_CHECKING` + `from __future__ import annotations`
- Done: `simulation_engine.py`
- Todo: all files in `core/`, `gameplay_management/`, `agents/`, `models/`
