# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "instructor",
#     "google-genai",
#     "python-dotenv",
#     "pydantic",
# ]
# ///
from core.simulation_engine import SimulationEngine
from core.bootstrap import *

if __name__ == "__main__":
    engine = create_engine()
    #engine.run(number_of_players = 3, generic_players=True, human_player = False)
    engine.run(number_of_players = 6, generic_players=False, human_player = True)