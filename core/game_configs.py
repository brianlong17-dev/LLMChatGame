from pydantic import BaseModel
from typing import Callable, Optional, List

from core.games import VoteAndGameManager

class GameDefinition(BaseModel):
    execute_game: Callable
    display_name: str
    rules_description: str

class VoteDefinition(BaseModel):
    execute_game: Callable
    display_name: str
    rules_description: str

class ImmunityDefinition(BaseModel):
    execute_game: Callable
    display_name: str
    rules_description: str
    #actually not the place for this since its flexible 
    is_public: bool = False  # Whether the immunity is known to all players or secret TODO will implement this later. its kind of complex to implment, well will need to be implemented into each voting phase game 
    is_secret: bool = False  # Whether the immunity is revealed to the players ahead of time

HIGHEST_POINT_IMMUNITY = ImmunityDefinition(
    display_name="Highest Points Player Immunity",
    rules_description=(
        "The player(s) with the highest points at the end of the phase receive immunity from the next vote. "
        "In the case of a tie, all tied players receive immunity."
    ),
    execute_game=VoteAndGameManager.get_highest_points_players_immunity 
)

WILDCARD_IMMUNITY = ImmunityDefinition(
    display_name="Wildcard Player Immunity",
    rules_description=(
        "The player deemed to be the most chaotic will receive immunity from the next vote. "
        "This is a one-off immunity that will be given once."
    ),
    execute_game=VoteAndGameManager.get_wildcard_player_immunity 
)
    
PRISONERS_DILEMMA = GameDefinition(
    display_name="Prisoner's Dilemma",
    rules_description="Each player will be paired another player, and play a round of prisoners dilemma. The points they potentially win will be added to their score",
    execute_game=VoteAndGameManager.run_game_prisoners_dilemma  # Note: no parentheses! We are passing the method itself.
)

EACH_PLAYER_VOTES_TO_REMOVE = VoteDefinition(
    display_name="Each player votes which player they want to remove",
    rules_description="The player that receives the most votes will be removed from the game...",
    execute_game=VoteAndGameManager.run_voting_round_basic
)