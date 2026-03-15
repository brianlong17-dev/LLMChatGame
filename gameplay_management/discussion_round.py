
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory

class DiscussionRound(BaseRound):
    
    def display_name(self):
        return "Discussion Round"
    
    def rules_description(self):
        topic = self.cfg().discussion_round_topic
        return (
            f"{topic}"
        )
        
        
    def _output_discussion_round_text(self, player, result):
        #TODO depreciate
        self.gameBoard.handle_public_private_output(player, result, override = True)
    
    @classmethod
    def is_discussion(cls):
        return True
    
    def run_game(self):
        for player in self.simulationEngine.agents:
            #-----------
            user_content =  "Time to discuss!"
            basic_model = DynamicModelFactory.create_model_(player, "basic_turn")
            result = player.take_turn_standard(user_content, self.gameBoard, basic_model)
            #----------
            self.gameBoard.new_turn_print() #why only here... probably on any public turn?
            self._output_discussion_round_text(player, result)
        
    