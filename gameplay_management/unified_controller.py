# INHERITANCE ORDER MATTERS: Mixins first, Base last.
from gameplay_management.base_manager import BaseManager
from gameplay_management.game_guess import GameGuess
from gameplay_management.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.game_targeted_choice import GameTargetedChoice
from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin
from gameplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin


class UnifiedController(GamePrisonersDilemma, GameTargetedChoice, GameGuess, VoteMechanicsMixin, ImmunityMechanicsMixin):
    def __init__(self, gameBoard, simulationEngine):
        # Initialize the BaseManager to set up self.gameBoard/self.simulationEngine
        super().__init__(gameBoard, simulationEngine)
     