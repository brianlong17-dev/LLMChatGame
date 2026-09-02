from __future__ import annotations

import os
import types
from typing import Literal, Optional, get_args, get_origin

from pydantic import BaseModel

os.environ.setdefault("DEV_MODE", "true")

from core.api_client.api_client import APIClient
from core.bootstrap import create_engine
from core.levels.phase_description import PhaseDescription
from core.sinks.game_sink import CapturingGameSink, NoopGameSink
from core.levels.game_designs.game_design_testing import TestingGameDesign


class UnscriptedChoice(Exception):
    pass


_STICKY = object()


ANY_ROUND = None


class ChoiceScript:

    def __init__(self, current_round):
        self._current_round = current_round
        self._queues: dict[tuple[str, str | None, str], list] = {}

    def set(self, speaker: str, field: str, value, in_round: str | None = ANY_ROUND) -> None:
        values = list(value) if isinstance(value, (list, tuple)) else [value, _STICKY]
        self._queues[(speaker, in_round, field)] = values

    def next(self, speaker: str, field: str, choices: tuple):
        round_name = self._current_round()
        found, value = self._pop(speaker, field, round_name)
        if not found:
            raise UnscriptedChoice(self._unscripted_message(speaker, field, choices, round_name))
        if value not in choices:
            raise UnscriptedChoice(
                f"During {round_name}: {speaker} was scripted to choose {value!r} for '{field}', "
                f"but the options were {list(choices)}.\n"
                f"If this field means different things in different rounds, scope it:\n"
                f"    game.chooses({speaker!r}, in_round={round_name}, {field}={choices[0]!r})"
            )
        return value

    def next_number(self, speaker: str, field: str):
        round_name = self._current_round()
        found, value = self._pop(speaker, field, round_name)
        if not found:
            raise UnscriptedChoice(
                f"Unscripted choice during {round_name}: {speaker} was asked to choose an amount for '{field}'.\n"
                f"Every choice is a real game decision — script it:\n"
                f"    game.chooses({speaker!r}, in_round={round_name}, {field}=0)"
            )
        return value

    def _pop(self, speaker: str, field: str, round_name):
        queue = self._queues.get((speaker, round_name, field))
        if queue is None:
            queue = self._queues.get((speaker, ANY_ROUND, field))
        if queue is None:
            return False, None
        if len(queue) > 1 and queue[1] is _STICKY:
            return True, queue[0]
        if len(queue) > 1:
            return True, queue.pop(0)
        return True, queue[0]

    def _unscripted_message(self, speaker, field, choices, round_name) -> str:
        return (
            f"Unscripted choice during {round_name}: {speaker} was asked for '{field}' "
            f"and the options were {list(choices)}.\n"
            f"Every choice is a real game decision — script it:\n"
            f"    game.chooses({speaker!r}, in_round={round_name}, {field}={choices[0]!r})"
        )


class ScriptedAPIClient(APIClient):

    def __init__(self, speaker_name: str, script: ChoiceScript):
        super().__init__(
            client=None,
            model="scripted",
            higher_model_name="scripted",
            sink=NoopGameSink(),
            token_budget=1,
        )
        self._mock_output = True
        self.speaker_name = speaker_name
        self.script = script
        self.last_requested_model = None

    def create(self, response_model, messages, **kwargs):
        self.last_requested_model = kwargs.get("agent_api_model")
        return self._build(response_model)

    def transcribe(self, audio_bytes, mime_type="audio/webm", model=None, hints=None):
        raise NotImplementedError("Transcription is not available in tests")

    def _build(self, response_model):
        values = {
            name: self._value_for(name, field.annotation)
            for name, field in response_model.model_fields.items()
        }
        return response_model(**values)

    def _value_for(self, name, annotation):
        annotation = _strip_optional(annotation)
        origin = get_origin(annotation)

        if origin is Literal:
            return self.script.next(self.speaker_name, name, get_args(annotation))
        if origin is list:
            inner = _strip_optional(get_args(annotation)[0]) if get_args(annotation) else str
            return [self._value_for(name, inner)]
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return self._build(annotation)
        if annotation is bool:
            return False
        if annotation is int:
            return self.script.next_number(self.speaker_name, name)
        if annotation is float:
            return 0.0
        return f"[{self.speaker_name} {name}]"


def _strip_optional(annotation):
    origin = get_origin(annotation)
    if origin is types.UnionType or str(origin) == "typing.Union":
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


class GameHarness:

    def __init__(self, players, phases, summarise_phases: bool = False):
        self.script = ChoiceScript(current_round=self._current_round)
        self.sink = CapturingGameSink()
        self._phases = [
            PhaseDescription(rounds=list(rounds), should_summarise_phase=summarise_phases)
            for rounds in phases
        ]
        self._phases_run = 0
        self._initialised = False
        self._engine = create_engine(
            self.sink,
            TestingGameDesign(self._phases),
            names=list(players),
            allow_rename=False,
            api_client=ScriptedAPIClient("Host", self.script),
            populate_agents=False,
        )
        for agent in self._engine.agents:
            agent.api_client = ScriptedAPIClient(agent.name, self.script)

    # --- Given ---

    def chooses(self, player: str, in_round=ANY_ROUND, **fields) -> "GameHarness":
        round_name = in_round.__name__ if isinstance(in_round, type) else in_round
        for field, value in fields.items():
            self.script.set(player, field, value, in_round=round_name)
        return self

    def votes_for(self, player: str, target: str, in_round=ANY_ROUND) -> "GameHarness":
        return self.chooses(player, in_round=in_round, target_name=target)

    def has_points(self, player: str, points: int) -> "GameHarness":
        self._initialise()
        self._board.append_agent_points(player, points)
        return self

    def configure(self, method: str, *args) -> "GameHarness":
        for phase in self._phases:
            phase.config_mutations.append((method, args))
        return self

    def uses_model(self, player: str, model_id: str) -> "GameHarness":
        self._agent(player).api_model = model_id
        return self

    def _current_round(self) -> str | None:
        runner = self._engine.phase_runner
        description = runner.current_phase_description
        if not description or not runner.current_round_index:
            return None
        return description.rounds[runner.current_round_index - 1].__name__

    # --- When ---

    def run(self) -> "GameHarness":
        while self._phases_run < len(self._phases) and not self._game_concluded():
            self.run_phase()
        return self

    def run_phase(self) -> "GameHarness":
        assert self._phases_run < len(self._phases), "No declared phases left to run"
        self._initialise()
        phase = self._phases[self._phases_run]
        self._phases_run += 1
        self._engine.phase_runner.run_phase(phase)
        return self

    def _game_concluded(self) -> bool:
        return self._board.game_over or len(self._engine.agents) <= 1

    def _initialise(self) -> None:
        if self._initialised:
            return
        self._engine.initialiseGameBoard()
        self._initialised = True

    # --- Then ---

    def score(self, player: str) -> int:
        if player in self._board.agent_scores:
            return self._board.get_agent_score(player)
        for update in reversed(self.sink.points_updates):
            if player in update:
                return update[player]
        raise AssertionError(f"'{player}' never held a score in this game")

    def scores(self) -> dict[str, int]:
        return dict(self._board.agent_scores)

    def survivors(self) -> list[str]:
        return [agent.name for agent in self._engine.agents]

    def eliminated(self) -> list[str]:
        return [agent.name for agent in self._engine.dead_agents]

    def is_eliminated(self, player: str) -> bool:
        return player in self.eliminated()

    def winner(self) -> str:
        survivors = self.survivors()
        assert len(survivors) == 1, f"Game has not concluded — survivors: {survivors}"
        return survivors[0]

    def widgets(self, kind: str) -> list[dict]:
        return [w for w in self.sink.widget_updates if w and w.get("kind") == kind]

    def widget_shown_with(self, speaker: str) -> dict:
        for action in reversed(self.sink.public_actions):
            if str(action["speaker"]) == speaker and action["widget"]:
                return action["widget"]
        raise AssertionError(f"No widget arrived attached to a message from '{speaker}'")

    def turn_by(self, actor: str) -> dict:
        for widget in reversed(self.widgets("give_take")):
            for turn in widget.get("turns", []):
                if turn["actor"] == actor and turn["state"] == "revealed":
                    return turn
        raise AssertionError(f"'{actor}' never took a turn in this game")

    def model_requested_by(self, player: str) -> str | None:
        return self._agent(player).api_client.last_requested_model

    def _agent(self, player: str):
        for agent in self._engine.agents:
            if agent.name == player:
                return agent
        raise AssertionError(f"'{player}' is not a player in this game")

    @property
    def _board(self):
        return self._engine.game_board


def guess_with_number(number: int):
    from gameplay_management.games.game_guess import GameGuess

    class ScriptedGuess(GameGuess):
        def _pick_winning_number(self, number_range):
            return number

    ScriptedGuess.__name__ = GameGuess.__name__
    ScriptedGuess.__qualname__ = GameGuess.__qualname__
    return ScriptedGuess


def start_game(players, rounds=None, phases=None, summarise_phases: bool = False) -> GameHarness:
    if (rounds is None) == (phases is None):
        raise ValueError("start_game takes exactly one of 'rounds' (a single phase) or 'phases'")
    return GameHarness(players, phases or [rounds], summarise_phases=summarise_phases)
