import os

from dotenv import load_dotenv
import instructor

from agents.character_generation.characterGeneration import CharacterGenerator
from agents.game_host import GameMaster
from core.gameboard import GameBoard
from core.sinks.console_sink import ConsoleGameEventSink
from core.phase_recipe_factory import PhaseRecipeFactoryDefault
from core.simulation_engine import SimulationEngine
from core.api_client import api_client


#gemini-2.0-flash-lite
#"gemini-3.1-flash-lite-preview",
#gemini-2.5-flash-lite
DEFAULT_MODEL_NAME = "gemini-3.1-flash-lite-preview"
DEFAULT_HIGHER_MODEL_NAME = "gemini-2.5-flash"


def create_engine(game_sink, number_of_players: int = 0, generic_players: bool = False, names=None,
                  agents = None,
                  allow_rename = True,
                  model_name=DEFAULT_MODEL_NAME, higher_model_name=DEFAULT_HIGHER_MODEL_NAME,
                  phase_factory=PhaseRecipeFactoryDefault):
    load_dotenv()
    client = instructor.from_provider('google/' + model_name, api_key=os.getenv("GEMINI_API_KEY"))
    api_client.init(client, model_name)
    game_master = GameMaster(model_name, higher_model_name=higher_model_name)
    gameBoard = GameBoard(game_sink)
    generator = CharacterGenerator(game_sink, model_name, higher_model_name)
    
    if agents:
        agents = agents
    elif names:
        agents = generator.generate_agents_from_names(names, allow_rename = allow_rename) 
    elif generic_players:
        agents = generator.genericPlayers(number_of_players)
    else:
        rand_names = generator.generate_random_debaters_names(number_of_players)
        agents = generator.generate_agents_from_names(rand_names, allow_rename = allow_rename)

    return SimulationEngine(agents=agents, game_board=gameBoard, game_master=game_master, generator=generator, phase_factory=phase_factory)