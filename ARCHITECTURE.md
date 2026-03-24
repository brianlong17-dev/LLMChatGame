# Architecture

A reality TV-style elimination game where LLM agents compete through discussion rounds, mini-games, and voting eliminations. Agents have evolving state and memory, and are eliminated until one winner remains.

---

## Components

### SimulationEngine
The top-level orchestrator. Holds references to all major components and owns the main game loop. Responsible for player setup, elimination, and delegating phase execution to the `PhaseRunner`.

### GameBoard
The central state object. Everything that needs to know about the current game state goes through here:
- Agent scores
- Message history (`RoundEntry` / `MessageEntry`)
- Phase and round counters
- Event broadcasting to the `GameEventSink`

Also owns the `ContextBuilder`.

### PhaseRunner
Drives phase and round execution. Given a `PhaseRecipe`, it iterates through the rounds, triggers introductions, dispatches to game or vote logic, requests round summaries from the `GameMaster`, and at the end of the phase runs agent memory summarisation in parallel.

### PhaseRecipeFactory
Decides what happens each phase — which games, votes, and immunities to include. Returns a `PhaseRecipe`. Encodes the game progression logic separately from execution.

### PhaseRecipe
A data object: an ordered list of round types and a list of immunity types. No logic — just a blueprint the `PhaseRunner` executes.

### UnifiedController (game_manager)
A single object that implements all game mechanics via multiple inheritance. Composed of mixins for every game type, vote type, and immunity type. The `PhaseRunner` calls into this object to run games and votes.

### BaseRound (and mixins)
Abstract base for all round types. Mixins add concrete behaviour — `is_vote()`, `is_game()`, `run_game()`, `run_vote()` etc. The `UnifiedController` inherits from all of them.

### Debater (agent)
The main player class. Holds all evolving agent state:
- `persona` — character description, updated each turn
- `strategy_to_win` — current strategic plan
- `life_lessons` — deque (max 8) of learned observations
- `speaking_style` — voice/tone
- `phase_summaries_detailed` / `phase_summaries_brief` — compressed phase memories

On each turn, the LLM response is parsed and these fields are updated in-place.

### GameMaster
A special LLM agent (name: "Host"). Summarises rounds into compressed text stored in a rolling deque. Can also select agents by parameter (e.g. "most chaotic") for wildcard immunity.

### ContextBuilder
Builds the context string passed to each agent on their turn. Filters message history by visibility — agents only see public messages and private conversations they were part of. Also builds the score dashboard string.

### DynamicModelFactory
Generates a Pydantic response model at runtime for each agent turn. The model is tailored to the turn type — it always includes `public_response`, `private_thoughts`, and the agent's cognitive fields (persona update, life lesson, strategy, etc.), plus any game-specific action fields (e.g. a `Literal["split", "steal"]` choice field).

### GameEventSink
Output abstraction. The `GameBoard` fires events (`on_round_start`, `on_public_action`, `on_private_conversation`, etc.) into the sink. `ConsoleGameEventSink` renders these to the terminal. Swap the sink to redirect output elsewhere.

---

## Data Model

### RoundEntry
Represents one round. Holds a list of `MessageEntry` objects, plus `phase_number` and `round_number`.

### MessageEntry
A group of messages with an optional `visibility_restriction: set[str]`. If `None`, the message is public. If a set of names, only those agents see it in their context.

---

## Agent Turn Flow

1. **Context built** — `ContextBuilder.get_full_context(agent)` returns recent round history filtered by visibility, plus scores
2. **System prompt built** — persona, speaking style, life lessons, strategy, score dashboard
3. **Dynamic model generated** — `DynamicModelFactory.create_model_()` tailored to the turn type
4. **LLM called** — via Instructor, returns a structured Pydantic object
5. **Cognitive fields processed** — `persona`, `strategy_to_win`, `life_lessons`, `speaking_style` updated on the agent

---

## Phase Flow

```
PhaseFactory.get_phase_recipe()
    → PhaseRecipe (ordered round types + immunity types)

PhaseRunner.run_phase(recipe)
    → gameBoard.new_phase()
    → for each round:
        gameBoard.newRound()            # creates RoundEntry
        _introduce_phase() if first     # host + system broadcasts
        round.run_game() or run_vote()  # dispatches to UnifiedController
        game_master.summariseRound()    # compresses round to text
        gameBoard.endRound()            # commits RoundEntry to history
    → agents.summarise_phase() (parallel)  # each agent writes phase memory
    → gameBoard.endPhase()
```

---

## Memory & Context Management

Agents maintain two layers of memory:

**Live state** (updated every turn): `persona`, `strategy_to_win`, `life_lessons`, `speaking_style`, `mathematical_assessment`

**Phase summaries** (written at phase end): each agent summarises the full phase using the higher model. Older phases are retained in brief form only; the most recent `detailed_summary_count` phases stay detailed. This prevents context length from growing unboundedly across a long game.

The `ContextBuilder` provides the current-phase round history. The agent's phase summaries cover everything before that.
