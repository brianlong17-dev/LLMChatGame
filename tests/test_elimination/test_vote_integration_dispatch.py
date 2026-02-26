from types import SimpleNamespace
from unittest.mock import MagicMock

from core.gameplay_definitions_config import EACH_PLAYER_VOTES_TO_REMOVE
from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin


def _player(name):
    player = MagicMock()
    player.name = name
    return player


def test_vote_definition_dispatch_runs_vote_and_applies_elimination_side_effects(monkeypatch):
    alice = _player("Alice")
    bob = _player("Bob")
    cara = _player("Cara")
    simulation = SimpleNamespace(agents=[alice, bob, cara])

    game_board = MagicMock()
    game_board.execution_style = False

    manager = VoteMechanicsMixin(game_board, simulation)
    manager.process_vote_rounds = MagicMock(
        return_value=("Bob", [SimpleNamespace(action="Bob"), SimpleNamespace(action="Alice")])
    )
    manager.publicPrivateResponse = MagicMock()
    manager.respond_to = MagicMock(return_value=SimpleNamespace(public_response="bye", private_thoughts="..."))

    monkeypatch.setattr(
        "gameplay_management.vote_mechanicsMixin.PromptLibrary.final_words_prompt",
        MagicMock(return_value="FINAL_WORDS_PROMPT"),
    )

    # Integration sanity: execute the configured vote definition callable.
    EACH_PLAYER_VOTES_TO_REMOVE.execute_game(manager, immunity_players=[])

    manager.process_vote_rounds.assert_called_once_with(["Alice", "Bob", "Cara"])
    assert [agent.name for agent in simulation.agents] == ["Alice", "Cara"]
    game_board.remove_agent_state.assert_called_once_with("Bob")
