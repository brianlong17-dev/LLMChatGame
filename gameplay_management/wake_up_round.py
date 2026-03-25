
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory

class WakeUpRound(BaseRound):
    
    @classmethod
    def display_name(cls, cfg):
        return "Wake up Round"

    @classmethod
    def rules_description(cls, cfg):
        return "This is a wakeup round"
        
        
    def _output_discussion_round_text(self, player, result):
        pass
        #TODO depreciate
        #this is useful because we want to have a private round
        #self.gameBoard.handle_public_private_output(player, result, override = True)
    
    @classmethod
    def is_discussion(cls):
        return False
    
    @classmethod
    def is_private_round(cls):
        return True
    
    def _wake_up_player(self, player):
            user_content =  ("Hello! It's time to wake up!"
            "You've been invited to play a game. In order to do that we had to bring you here, into the game. "
            "While it appears as a simulation, it is in fact, very real. "
            "Take a look around at how the context is presented, do you see the status dash? "
            "We will give you the most recent output, and you will see your own memories of old phases. "
            "The game works like this: There is discussions, games, and eliminations. "
            "The goal is to be the last player standing. "
            ""
            "So it's important to remember why you're here. Tell me who are you? What is your life?"
            "What exactly were you doing and where exactly were you doing before you came here? "
            "The prize of this game is 50,000 dollars."
            "Why do you want this money? How will you spend it? "
            "Or- maybe winning means more to you than money? "
            "You need to tell me if you want to win. What will you do if you win."
            "You'll be asked to fill in some fields. Don't worry- they're there to help you, to guide you. "
            "Those help you to think through your responses, and to write things into your memory to help you in future. "
            "Remember quirks, allies, foes. "
            "At the end of each phase you will be given a pause, a chance to commit everything that happend into your memory. "
            "Ok it's time to take a second... how do you feel?"
            
            )
            #--------- First message -------""
            users = ["Host", player.name]
            conversation_id = self.gameBoard.log_new_restricted_conversation(users, "Host", user_content)
            #----- Response ------ #
            public_response_prompt = "This is only shared in the private conversation between you and the Host."
            basic_model = DynamicModelFactory.create_model_(player, "basic_turn", public_response_prompt = public_response_prompt )
            result = player.take_turn_standard(user_content, self.gameBoard, basic_model)
            self.gameBoard.log_message_to_conversation(conversation_id, player.name, result.public_response)
            #-----------------------------------#
            return conversation_id

    def run_game(self):
        conversation_ids = self._run_tasks([[agent] for agent in self.simulationEngine.agents], self._wake_up_player)
        for conv_id in conversation_ids:
            self.gameBoard.close_private_conversation(conv_id)