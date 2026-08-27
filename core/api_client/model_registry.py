from typing import List, Optional
from core.api_client.model_definition import ModelOption

MODEL_3_5 = "gemini-3.5-flash-lite"
MODEL_3 = "gemini-3.1-flash-lite"
MODEL_2 = "gemini-2.5-flash-lite"
DEFAULT_MODEL_NAME = MODEL_3
DEFAULT_HIGHER_MODEL_NAME = "gemini-3.5-flash"


AVAILABLE_MODELS: List[ModelOption] = [
    ModelOption(id=MODEL_2, name="Gemini 2.5 Flash Lite", default=MODEL_2 == DEFAULT_MODEL_NAME),
    ModelOption(id=MODEL_3, name="Gemini 3.1 Flash Lite", default=MODEL_3 == DEFAULT_MODEL_NAME),
    ModelOption(id=MODEL_3_5, name="Gemini 3.5 Flash Lite", default=MODEL_3_5 == DEFAULT_MODEL_NAME),
]


def get_model_by_id(model_id: str) -> Optional[ModelOption]:
    """Retrieve a model option by its id."""
    for model in AVAILABLE_MODELS:
        if model.id == model_id:
            return model
    return None


def get_available_models() -> List[ModelOption]:
    """Get all available model options."""
    return AVAILABLE_MODELS
