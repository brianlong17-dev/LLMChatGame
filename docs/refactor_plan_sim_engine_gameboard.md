# SimulationEngine + GameBoard Refactor Plan

## Objective
Make simulation/gameflow easier to set up and test while preserving current behavior.

## Plan
1. Stabilize boundaries first.
- Keep gameplay behavior identical while refactoring internals.
- Freeze with a small regression set before changes (`give`, `steal/sacrifice`, one full phase run).

2. Extract runtime wiring from `SimulationEngine`.
- Move env loading + provider creation into a bootstrap/factory function.
- Keep `SimulationEngine` constructor pure and dependency-injected.
- Constructor accepts `client`, `game_master`, `generator`, `game_manager`, `game_board` (or factories).
- Keep defaults so current app entrypoints continue to work.

3. Add a test-oriented engine constructor path.
- Add `SimulationEngine.for_tests(...)` (or an equivalent builder).
- Takes prebuilt agents, fake client/game master, and deterministic setup.
- Avoids external API/env bootstrapping.

4. Split `GameBoard` responsibilities.
- Keep state mutation + event recording in `GameBoard`.
- Move `ConsoleRenderer` usage behind an injected sink/renderer interface.
- Default sink prints to console; test sink stores events for assertions.
- Maintain current method signatures initially for compatibility.

5. Normalize event and summary models.
- Define typed structures (for example `RoundSummary`, `BoardEvent`).
- Refactor `newRound()` to consume one summary shape only.
- Remove mixed iterable/object handling assumptions.

6. Inject randomness strategy.
- Introduce RNG/turn-order dependency (`random.Random` or strategy object).
- Route all randomness through it (`_shuffled_agents`, random picks).
- Tests use seeded RNG or fixed-order strategy.

7. Fix low-risk correctness issues while touching code.
- Fix `GameBoard.system_broadcast_no_name` (`self.gameBoard` reference bug).
- Add clear guardrails/errors for missing agent state where needed.

8. Migrate tests in phases.
- Phase A: Keep old tests passing via backward-compatible defaults.
- Phase B: Move integration tests to `for_tests`/shared builders.
- Phase C: Remove legacy monkeypatch-heavy setup once stable.

9. Definition of done.
- No network/env setup required for core gameflow tests.
- Engine + board can be test-instantiated in under ~10 lines.
- Deterministic randomness in tests by default.
- Renderer side effects are optional and isolated.

## Suggested File-by-File Execution Order
1. `core/simulation_engine.py`
- Add dependency-injected constructor parameters with safe defaults.
- Add `for_tests(...)`.

2. New bootstrap module (for example `core/bootstrap.py`)
- Move `load_dotenv()` and provider wiring here.

3. `core/gameboard.py`
- Introduce renderer/event-sink abstraction.
- Keep existing methods as facade to limit call-site churn.

4. `gameplay_management/base_manager.py`
- Route randomness through injected RNG/strategy.

5. `tests/helpers/` and integration tests
- Standardize on shared builders using `for_tests(...)`.

6. Cleanup pass
- Remove temporary compatibility shims once all tests are migrated.
