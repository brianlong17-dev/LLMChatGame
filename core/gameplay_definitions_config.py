from pydantic import BaseModel
from typing import Callable, Optional, List
from gameplay_management.base_manager import *
from gameplay_management.game_guess import GameGuess
from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.game_targeted_choice import GameTargetedChoice
from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin

from prompts.gamePrompts import GamePromptLibrary

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

##############################################
# GAMES                                      #
##############################################

GUESS= GameDefinition(
    display_name="Guess the number",
    rules_description="Guess the correct number to win points !",
    execute_game=GameGuess.run_game_guess_the_number
)


GIVER= GameDefinition(
    display_name="Giver",
    rules_description="Choose a player to recieve points !",
    execute_game=GameTargetedChoice.run_game_give
)

STEALER= GameDefinition(
    display_name="Stealer",
    rules_description="Choose a player to steal points from!",
    execute_game=GameTargetedChoice.run_game_steal
)

SACRIFICER= GameDefinition(
    display_name="Sacrificer",
    rules_description="Use your own points to hurt another player",
    execute_game=GameTargetedChoice.run_game_sacrifice_points
)

PRISONERS_DILEMMA= GameDefinition(
    display_name="Prisoner's Dilemma",
    rules_description=f"At random, players will be assigned parters. {GamePromptLibrary.pd_desc_string}",
    execute_game=GamePrisonersDilemma.run_game_prisoners_dilemma  # Note: no parentheses! We are passing the method itself.
)

PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_RANDOM= GameDefinition(
    display_name="Prisoner's Dilemma",
    rules_description=f"In a random order, players will get to choose their partners. {GamePromptLibrary.pd_desc_string}",
    execute_game=GamePrisonersDilemma.run_game_prisoners_dilemma_choose_partner  # Note: no parentheses! We are passing the method itself.
)

PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_WINNER = GameDefinition(
    display_name="Prisoner's Dilemma",
    rules_description=f"The player with the highest score will get to pick their partner, and so on. Each pair will play a round. {GamePromptLibrary.pd_desc_string}",
    execute_game=GamePrisonersDilemma.run_game_prisoners_dilemma_choose_partner_winner  # Note: no parentheses! We are passing the method itself.
)

PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER = GameDefinition(
    display_name="Prisoner's Dilemma",
    rules_description=f"The player with the lowest score will get to pick their partner, and so on. {GamePromptLibrary.pd_desc_string}",
    execute_game=GamePrisonersDilemma.run_game_prisoners_dilemma_choose_partner_loser  # Note: no parentheses! We are passing the method itself.
)

##############################################
# Eliminations                               #
##############################################

EACH_PLAYER_VOTES_TO_REMOVE_BOTTOM_TWO = VoteDefinition(
    display_name="Two players with the lowest scores face elimination.",
    rules_description="Two players with the lowest scores face elimination. Each player will vote who they want to send home",
    execute_game=VoteMechanicsMixin.run_voting_bottom_two_only_two
)

EACH_PLAYER_VOTES_TO_REMOVE_BOTTOM_TWO_MULTIPLE = VoteDefinition(
    display_name="The players with the lowest scores face elimination.",
    rules_description="The two players with the lowest scores are up for elimination. In the event of a tie for the bottom spots, all tied players will also face the vote. more players will face elimination Each player will vote who they want to send home",
    execute_game=VoteMechanicsMixin.run_voting_bottom_two_multiple
)

EACH_PLAYER_VOTES_TO_REMOVE = VoteDefinition(
    display_name="Each player votes which player they want to remove",
    rules_description="The player that receives the most votes will be removed from the game...",
    execute_game=VoteMechanicsMixin.run_voting_round_basic
)

EACH_PLAYER_VOTES_TO_REMOVE_BEST_NOT_MISS = VoteDefinition(
    display_name="Vote a player out, but don't miss.",
    rules_description="Each player votes which player they want to remove. Any players voted for but not removed will gain a point for each vote against them.",
    execute_game=VoteMechanicsMixin.run_voting_round_basic_dont_miss
)

LOWEST_POINTS_REMOVED = VoteDefinition(
    display_name="Player with the lowest points is removed from the game",
    rules_description="The player with the lowest points will be removed from the game IMMEDATELY..",
    execute_game=VoteMechanicsMixin.run_voting_lowest_points_removed
)

WINNER_CHOOSES = VoteDefinition(
    display_name="The Leader Executes",
    rules_description="The player leading the scores will choose who leaves the game IMMEDATELY..",
    execute_game=VoteMechanicsMixin.run_voting_winner_chooses
)

##############################################
# Immunities                                 #
##############################################


HIGHEST_POINT_IMMUNITY = ImmunityDefinition(
    display_name="Highest Points Player Immunity",
    rules_description=(
        "The player(s) with the highest points at the end of the phase receive immunity from the next vote. "
        "In the case of a tie, all tied players receive immunity."
    ),
    execute_game=ImmunityMechanicsMixin.get_highest_points_players_immunity 
)

HIGHEST_POINT_IMMUNITY_ONLY_ONE = ImmunityDefinition(
    display_name="Highest Points Player Immunity",
    rules_description=(
        "The player with the highest points at the end of the phase receive immunity from the next vote."
        "In the case of a tie, one player is randomly selected to receive immunity."
    ),
    execute_game=ImmunityMechanicsMixin.get_highest_points_players_immunity_only_one
)

WILDCARD_IMMUNITY = ImmunityDefinition(
    display_name="Wildcard Player Immunity",
    rules_description=(
        "The player deemed to be the most chaotic will receive immunity from the next vote. "
        "This is a one-off immunity that will be given once."
    ),
    execute_game=ImmunityMechanicsMixin.get_wildcard_player_immunity 
)
