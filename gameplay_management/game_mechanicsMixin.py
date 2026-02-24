from pydantic import Field
from gameplay_management.base_manager import BaseManager
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
import random
from typing import TYPE_CHECKING, Dict, Literal

if TYPE_CHECKING:
    from agents.player import Debater

class GameMechanicsMixin(BaseManager):
    
    def m(self):
        return None
