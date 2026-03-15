# INHERITANCE ORDER MATTERS: Mixins first, Base last.
from gameplay_management.base_manager import BaseRound
from gameplay_management.discussion_round import DiscussionRound
from gameplay_management.eliminations.voting_bottom_two import VoteBottomTwo
from gameplay_management.eliminations.voting_each_player import VoteEachPlayer
from gameplay_management.eliminations.voting_lowest_points import VoteLowestPoints
from gameplay_management.eliminations.voting_winner_chooses import VoteWinnerChooses
from gameplay_management.games.game_guess import GameGuess
from gameplay_management.games.game_perform import GamePerformSobStory
from gameplay_management.games.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.game_targeted.game_targeted_choice import GameTargetedChoice
from gameplay_management.game_targeted.game_targeted_give import GameTargetedChoiceGive
from gameplay_management.game_targeted.game_targeted_sacrifice import GameTargetedChoiceSacrifice
from gameplay_management.game_targeted.game_targeted_steal import GameTargetedChoiceSteal
from gameplay_management.immunities.highest_points_immunity import HighestPointsImmunity
from gameplay_management.immunities.wildcard_immunity import WildcardImmunity
from gameplay_management.immunities.immunity_mechanicsMixin import ImmunityMechanicsMixin
from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin


class UnifiedController(GamePrisonersDilemma, GameGuess, GamePerformSobStory, 
                        GameTargetedChoiceGive, GameTargetedChoiceSteal, GameTargetedChoiceSacrifice, GameTargetedChoice,
                        VoteBottomTwo, VoteEachPlayer, VoteLowestPoints, VoteWinnerChooses, VoteMechanicsMixin, 
                        WildcardImmunity, HighestPointsImmunity, ImmunityMechanicsMixin, 
                        DiscussionRound,
                        BaseRound):
    def __init__(self, gameBoard, simulationEngine):
        # Initialize the BaseManager to set up self.gameBoard/self.simulationEngine
        super().__init__(gameBoard, simulationEngine)
     