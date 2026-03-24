from gameplay_management.base_manager import BaseRound
#from core.gameboard import GameBoard
import random


class ImmunityMechanicsMixin(BaseRound):
    def __init__(self, gameBoard, simulationEngine):
        super().__init__(gameBoard, simulationEngine) 
    
    
    @classmethod
    def _validate_immunity_names(cls, immunity_type, immunity_names, cfg, agents):
        #goes without saying this has no business here - should go to the immunity super class
        if not isinstance(immunity_names, list):
            raise TypeError(
                f"Immunity '{immunity_type.display_name(cfg)}' must return list[str], got {type(immunity_names).__name__}"
            )
        if not all(isinstance(name, str) for name in immunity_names):
            raise TypeError(
                f"Immunity '{immunity_type.display_name(cfg)}' must return list[str], got non-string values: {immunity_names!r}"
            )
        active_player_names = {agent.name for agent in agents}
        invalid_names = [name for name in immunity_names if name not in active_player_names]
        if invalid_names:
            raise ValueError(
                f"Immunity '{immunity_type.display_name(cfg)}' returned unknown player name(s): {invalid_names}"
            )
      
                    
    
