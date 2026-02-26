from types import SimpleNamespace

from agents.player import Debater
from core.gameboard import GameBoard
from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.game_targeted_choice import GameTargetedChoice
from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin


def turn_payload(target_name=None, public_response="pub", private_thoughts="priv", **extra_fields):
    payload = {
        "public_response": public_response,
        "private_thoughts": private_thoughts,
        **extra_fields,
    }
    if target_name is not None:
        payload["target_name"] = target_name
    return payload


class QueuedClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("API client called more times than expected")
        return SimpleNamespace(**self._responses.pop(0))

    def assert_exhausted(self):
        assert not self._responses, f"Unused queued responses: {len(self._responses)}"


class NoopGameMaster:
    pass


def make_debater(name, client, model_name="test-model"):
    return Debater(
        name=name,
        initial_persona=f"{name} persona",
        initial_form=f"{name} form",
        client=client,
        model_name=model_name,
        speaking_style="normal",
    )


def host_messages(board):
    return [entry["message"] for entry in board.currentRound if entry["speaker"] == "HOST"]


def messages_for(board, speaker):
    return [entry["message"] for entry in board.currentRound if entry["speaker"] == speaker]


def build_targeted_choice_game(agent_specs, initial_scores=None):
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [make_debater(name, clients[name]) for name in agent_specs]

    board = GameBoard(NoopGameMaster())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = SimpleNamespace(agents=agents)
    game = GameTargetedChoice(board, simulation)
    game._shuffled_agents = lambda: list(simulation.agents)
    return game, board, agents, clients


def build_pd_game(agent_specs, initial_scores=None):
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [make_debater(name, clients[name]) for name in agent_specs]

    board = GameBoard(NoopGameMaster())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = SimpleNamespace(agents=agents)
    game = GamePrisonersDilemma(board, simulation)
    return game, board, agents, clients


def build_vote_game(agent_specs, initial_scores=None, execution_style=False):
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [make_debater(name, clients[name]) for name in agent_specs]

    board = GameBoard(NoopGameMaster())
    board.execution_style = execution_style
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = SimpleNamespace(agents=agents)
    manager = VoteMechanicsMixin(board, simulation)
    return manager, board, agents, clients
