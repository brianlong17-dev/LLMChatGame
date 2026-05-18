from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.player import Debater

class GameMechanicsMixin(BaseRound):
    
    def _generate_random_pairings(self, agents):
        pairs = []
        # Work on a copy if you don't want to mutate the original list
        available = agents[:] 
        random.shuffle(available)
        
        while len(available) >= 2:
            pair = (available.pop(), available.pop())
            pairs.append(pair)
        leftover = available[0] if available else None
        return pairs, leftover
        
    
    
    @classmethod
    def is_game(cls):
        return True
    
    
