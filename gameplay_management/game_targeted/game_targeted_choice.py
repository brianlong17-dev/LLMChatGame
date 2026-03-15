from pydantic import Field, create_model
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary

class GameTargetedChoice(GameMechanicsMixin):
    def display_name(self):
        return "Targeted Choice"

    def get_error_model(self, message: str):
    # This creates a NEW class where the default value is your specific message
        return create_model("Error", error_string=(str, message))
    
    def get_error_string(self, model_class):
        if GamePromptLibrary.model_field_error in model_class.model_fields:
            return model_class().error_string
        return None

    def _normalize_target_string(self, target: str):
        return str(target).strip().lower() if target is not None else ""

    def _clean_target_name(self, target: str):
        if target is None:
            return None
        cleaned = str(target).strip()
        return cleaned or None
    
    def run_targeted_round(self, game_intro, player_intro, game_instruction, logic_callback, response_model_callback, validate_name=True):
        self.gameBoard.host_broadcast(game_intro)
        available_agents = self._shuffled_agents()
        
        for player in available_agents:
            self.gameBoard.host_broadcast(player_intro.format(player_name=player.name))
            
            #---Generate model, check if error----#
            response_model = response_model_callback(player)
            error = self.get_error_string(response_model)
            if error:
                result_host_string = error
                player_for_reaction = player
                            
                
            else:
                response = player.take_turn_standard(game_instruction, self.gameBoard, response_model)
                self.publicPrivateResponse(player, response)
                
                target_name = getattr(response, GamePromptLibrary.model_field_choose_name)
                target_agent = self._agent_by_name(self._clean_target_name(target_name))
                
                if validate_name and (not target_agent or target_agent.name == player.name):
                    result_host_string = GamePromptLibrary.invalid_target_message.format(
                        player_name=player.name,
                        target_name=target_name,
                    )
                    player_for_reaction = player
                else:
                    # Execute the specific logic (Give vs Steal vs Sacrifice)
                    result_host_string, player_for_reaction = logic_callback(player, target_agent, response)
                    
            self.gameBoard.host_broadcast(result_host_string)
            reaction = self.respond_to(player_for_reaction, result_host_string)
            self.publicPrivateResponse(player_for_reaction, reaction)
            self.gameBoard.system_broadcast(self.gameBoard.agent_scores, private = True)
   