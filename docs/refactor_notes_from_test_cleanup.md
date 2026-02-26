# Refactor Notes From Test Cleanup

## High-value code refactors observed

1. `GameTargetedChoice.get_error_string` still checks deprecated Pydantic `__fields__`.
- Location: `gameplay_management/game_targeted_choice.py`
- Tests now emit warnings. Move to `model_fields` only for Pydantic v2 compatibility.

2. `SimulationEngine` still mixes orchestration with provider/env bootstrap.
- Location: `core/simulation_engine.py`
- Splitting construction/bootstrap from runtime orchestration would keep tests fast and deterministic.

3. `GameBoard` mixes state/event recording with console rendering side effects.
- Location: `core/gameboard.py`
- A renderer/event-sink abstraction would simplify assertions and remove print noise in tests.

4. `run_targeted_round` assumes response always has `target_name`.
- Location: `gameplay_management/game_targeted_choice.py`
- A defensive `getattr(..., None)` with invalid-target fallback would prevent hard crashes from malformed model output.

5. Voting internals are hard to test because `ThreadPoolExecutor` is hard-coded.
- Location: `gameplay_management/vote_mechanicsMixin.py`
- Inject an executor strategy (or serial mode switch) for deterministic tests.

6. `VoteMechanicsMixin.eliminate_player_by_name` mutates state before collecting final words.
- Location: `gameplay_management/vote_mechanicsMixin.py`
- Consider collecting final words first or explicitly documenting the post-elimination prompt semantics.

7. `run_voting_bottom_two` has likely logic bugs.
- Location: `gameplay_management/vote_mechanicsMixin.py`
- It passes name lists into `get_strategic_player`, mutates lists inline with `.remove(...)`, and likely sends wrong types. Needs targeted cleanup before wider usage.

8. `GameBoard.system_broadcast_no_name` references `self.gameBoard` from inside `GameBoard`.
- Location: `core/gameboard.py`
- Should call `self.broadcast_public_action(...)` directly.

9. Randomness is spread across modules and directly imported.
- Locations: multiple (`game_mechanicsMixin.py`, `vote_mechanicsMixin.py`, `immunity_mechanicsMixin.py`, `game_prisoners_dilemma.py`)
- Injecting RNG/strategy objects would eliminate monkeypatching and improve reproducibility.

10. Some manager methods take/return loosely typed `SimpleNamespace`-like objects.
- Locations: gameplay manager mixins
- Introduce explicit response protocols/models for stronger contracts and easier refactor safety.
