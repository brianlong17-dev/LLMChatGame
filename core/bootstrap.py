import os

from dotenv import load_dotenv
import instructor

from agents.character_generation.characterGeneration import CharacterGenerator
from agents.gameMaster import GameMaster
from core.gameboard import GameBoard
from core.sinks.console_sink import ConsoleGameEventSink
from core.phase_recipe_factory import PhaseRecipeFactoryDefault
from core.simulation_engine import SimulationEngine


def create_engine(game_sink, number_of_players: int = 0, generic_players: bool = False, names=None,
                  allow_rename = True,
                  model_name="gemini-2.0-flash-lite", higher_model_name="gemini-2.5-flash",
                  phase_factory=PhaseRecipeFactoryDefault):
    load_dotenv()
    client = instructor.from_provider('google/' + model_name, api_key=os.getenv("GEMINI_API_KEY"))
    game_master = GameMaster(client, model_name, higher_model_name=higher_model_name)
    gameBoard = GameBoard(game_sink)
    generator = CharacterGenerator(game_sink, client, model_name, higher_model_name)
    
    if names:
        agents = generator.generate_agents_from_names(names, allow_rename = allow_rename) 
    elif generic_players:
        agents = generator.genericPlayers(number_of_players)
    else:
        rand_names = generator.generate_random_debaters_names(number_of_players)
        agents = generator.generate_agents_from_names(rand_names, allow_rename = allow_rename)

    return SimulationEngine(agents=agents, game_board=gameBoard, game_master=game_master, generator=generator, phase_factory=phase_factory)