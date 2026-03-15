import os

from dotenv import load_dotenv
import instructor

from agents.character_generation.characterGeneration import CharacterGenerator
from agents.gameMaster import GameMaster
from core.gameboard import GameBoard
from core.sinks.console_sink import ConsoleGameEventSink
from core.phase_recipe import PhaseRecipeFactoryDefault
from core.simulation_engine import SimulationEngine


def create_engine(model_name="gemini-2.0-flash-lite", higher_model_name="gemini-2.5-flash", 
                  phase_factory=PhaseRecipeFactoryDefault, game_sink_class= ConsoleGameEventSink):
    load_dotenv()
    client = instructor.from_provider('google/' + model_name, api_key=os.getenv("GEMINI_API_KEY"))
    game_master = GameMaster(client, model_name, higher_model_name=higher_model_name)
    game_sink = game_sink_class()
    gameBoard = GameBoard(game_sink)
    generator = CharacterGenerator(gameBoard, client, model_name, higher_model_name)
    return SimulationEngine(game_board = gameBoard, game_master=game_master, generator=generator, phase_factory=phase_factory)