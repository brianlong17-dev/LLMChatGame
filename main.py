# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "instructor",
#     "google-genai",
#     "python-dotenv",
#     "pydantic",
# ]
# ///
from core.bootstrap import *

if __name__ == "__main__":
    sink = ConsoleGameEventSink() 
    engine = create_engine(sink, number_of_players = 8, generic_players=False)
    engine.run( human_player_name = "")
