"""
Builds blank Debater agents for deterministic test runs.
Skips the LLM character generation step — persona/speaking_style are
populated downstream from saved agent state.
"""
from agents.player import Debater
from core.bootstrap import DEFAULT_MODEL_NAME, DEFAULT_HIGHER_MODEL_NAME


def build_hardcoded_debaters(names):
    return [
        Debater(
            name=name,
            initial_persona="",
            model_name=DEFAULT_MODEL_NAME,
            higher_model_name=DEFAULT_HIGHER_MODEL_NAME,
            speaking_style="",
        )
        for name in names
    ]
