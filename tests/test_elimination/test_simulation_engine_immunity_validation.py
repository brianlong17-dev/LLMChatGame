from types import SimpleNamespace

import pytest

from core.phase_runner import PhaseRunner
from gameplay_management.immunities.immunity_mechanicsMixin import ImmunityMechanicsMixin


def _immunity_type(display_name="Bad immunity"):
    return SimpleNamespace(display_name=lambda _gm: display_name)


def test_validate_immunity_raises_if_immunity_returns_non_list():
    with pytest.raises(TypeError, match="must return list\\[str\\]"):
        ImmunityMechanicsMixin._validate_immunity(
            _immunity_type(),
            "Alice",
            SimpleNamespace(),
            [SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob")],
        )


def test_validate_immunity_raises_if_immunity_returns_non_string_entries():
    with pytest.raises(TypeError, match="must return list\\[str\\]"):
        ImmunityMechanicsMixin._validate_immunity(
            _immunity_type(),
            ["Alice", 123],
            SimpleNamespace(),
            [SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob")],
        )


def test_validate_immunity_raises_if_immunity_returns_unknown_player_name():
    with pytest.raises(ValueError, match="unknown player name"):
        ImmunityMechanicsMixin._validate_immunity(
            _immunity_type(),
            ["Ghost"],
            SimpleNamespace(),
            [SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob")],
        )


def test_phase_runner_dedupes_immunity_names_before_vote_dispatch():
    seen = []
    runner = PhaseRunner.__new__(PhaseRunner)
    runner.game_manager = SimpleNamespace()

    round_obj = SimpleNamespace(
        run_vote=lambda _manager, immunity_players=None: seen.append(list(immunity_players))
    )
    immunity_types = [
        SimpleNamespace(run_immunity=lambda _manager: ["Alice", "Bob"]),
        SimpleNamespace(run_immunity=lambda _manager: ["Bob", "Alice", "Alice"]),
    ]

    PhaseRunner.run_vote_round_with_immunity_types(runner, round_obj, immunity_types)

    assert seen == [["Alice", "Bob"]]
