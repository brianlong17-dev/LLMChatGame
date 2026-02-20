# INHERITANCE ORDER MATTERS: Mixins first, Base last.
from gamplay_management.base_manager import BaseManager
from gamplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin
from gamplay_management.vote_mechanicsMixin import VoteMechanicsMixin
from gamplay_management.game_mechanicsMixin import GameMechanicsMixin


class UnifiedController(GameMechanicsMixin, VoteMechanicsMixin, ImmunityMechanicsMixin, BaseManager):
    def __init__(self, gameBoard, simulationEngine):
        # Initialize the BaseManager to set up self.gameBoard/self.simulationEngine
        super().__init__(gameBoard, simulationEngine)
     