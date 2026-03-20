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
    engine.run(number_of_players = 7, generic_players=False, human_player = False)