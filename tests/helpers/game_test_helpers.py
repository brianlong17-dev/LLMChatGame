from types import SimpleNamespace

from agents.player import Debater
from core.game_config import GameConfig
from core.gameboard import GameBoard
from core.phase_runner import PhaseRunner
from gameplay_management.unified_controller import UnifiedController


def turn_payload(target_name=None, public_response="pub", private_thoughts="priv", **extra_fields):
    payload = {
        "public_response": public_response,
        "private_thoughts": private_thoughts,
        **extra_fields,
    }
    if target_name is not None:
        payload["target_name"] = target_name
    return payload


class _QueuedResponse(SimpleNamespace):
    def model_dump(self):
        return dict(vars(self))


class TestGameSink:
    def get_user_input_simple(self, field_name, description):
        raise RuntimeError("TestGameSink cannot collect user input")

    def get_user_input_multiple_choice(self, field_name, description, choices):
        raise RuntimeError("TestGameSink cannot collect user input")

    def on_game_intro(self, message): pass
    def on_game_over(self, winner_name): pass
    def on_phase_header(self, phase_number): pass
    def on_phase_intro(self, host_text, summary_text): pass
    def on_round_start(self, round_number, scores): pass
    def on_round_summary(self, summary): pass
    def on_turn_header(self, turn_number): pass
    def on_public_action(self, speaker, message, color=""): pass
    def on_private_thought(self, speaker, message): pass
    def on_inner_workings(self, speaker, inner_workings, override=False): pass
    def system_private(self, message): pass
    def delay(self, delay): pass
    def on_points_update(self, points): pass


class QueuedClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("API client called more times than expected")
        return _QueuedResponse(**self._responses.pop(0))

    def assert_exhausted(self):
        assert not self._responses, f"Unused queued responses: {len(self._responses)}"


class NoopGameMaster:
    def summariseRound(self, *_args, **_kwargs):
        return SimpleNamespace(round_summary="")


class TestSimulation:
    __test__ = False

    def __init__(self, agents, gameplay_config=None):
        self.agents = list(agents)
        self.dead_agents = []
        self.gameplay_config = gameplay_config or GameConfig()
        self.gameBoard = None
        self.game_manager = None

    def eliminate_player(self, agent):
        self.agents.remove(agent)
        self.dead_agents.append(agent)


def attach_test_runtime(board, simulation, game_manager, game_master=None):
    simulation.gameBoard = board
    simulation.game_manager = game_manager
    simulation.game_master = game_master or NoopGameMaster()
    board.phase_runner = PhaseRunner(simulation)
    return game_manager


def make_debater(name, client, model_name="test-model"):
    return Debater(
        name=name,
        initial_persona=f"{name} persona",
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

    board = GameBoard(TestGameSink())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = TestSimulation(agents)
    game = UnifiedController(board, simulation)
    attach_test_runtime(board, simulation, game)
    game._shuffled_agents = lambda: list(simulation.agents)
    return game, board, agents, clients


def build_pd_game(agent_specs, initial_scores=None):
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [make_debater(name, clients[name]) for name in agent_specs]

    board = GameBoard(TestGameSink())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = TestSimulation(agents)
    game = UnifiedController(board, simulation)
    attach_test_runtime(board, simulation, game)
    return game, board, agents, clients


def build_guess_game(agent_specs, initial_scores=None):
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [make_debater(name, clients[name]) for name in agent_specs]

    board = GameBoard(TestGameSink())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = TestSimulation(agents)
    simulation.gameplay_config.guess_number_range = 4
    game = UnifiedController(board, simulation)
    attach_test_runtime(board, simulation, game)
    return game, board, agents, clients


def build_vote_game(agent_specs, initial_scores=None, execution_style=False):
    clients = {name: QueuedClient(responses) for name, responses in agent_specs.items()}
    agents = [make_debater(name, clients[name]) for name in agent_specs]

    board = GameBoard(TestGameSink())
    board.initialize_agents(agents)
    if initial_scores:
        for name, score in initial_scores.items():
            if name in board.agent_scores:
                board.agent_scores[name] = score

    simulation = TestSimulation(agents)
    simulation.gameplay_config.execution_style = execution_style
    manager = UnifiedController(board, simulation)
    attach_test_runtime(board, simulation, manager)
    return manager, board, agents, clients
