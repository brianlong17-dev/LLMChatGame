"""
Generates a single character and prints the result.
Swap the name to test different characters.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
import google.genai as genai
from core.api_client import api_client
from core.bootstrap import DEFAULT_MODEL_NAME, DEFAULT_HIGHER_MODEL_NAME
from core.sinks.console_sink import ConsoleGameEventSink
from agents.character_generation.characterGeneration import CharacterGenerator

if __name__ == "__main__":
    load_dotenv()
    client = genai.Client(
        vertexai=True,
        project=os.getenv("PROJECT"),
        location=os.getenv("LOCATION"),
    )
    api_client.init(client, DEFAULT_MODEL_NAME)

    sink = ConsoleGameEventSink()
    generator = CharacterGenerator(sink, DEFAULT_MODEL_NAME, DEFAULT_HIGHER_MODEL_NAME)

    mj = generator.generate_debater("Lady Diana", allow_rename=False)
    print(f"Name: {mj.name}")
    print(f"\nPersona:\n{mj.persona}")
    print(f"\nSpeaking Style:\n{mj.speaking_style}")
