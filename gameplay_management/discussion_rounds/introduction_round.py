
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory

class IntroRound(BaseRound):
    
    @classmethod
    def display_name(cls, cfg):
        return "Intro Round"

    @classmethod
    def rules_description(cls, cfg):
        return "This is a wakeup round"
    
    @classmethod
    def is_discussion(cls):
        return False
    
    @classmethod
    def is_private_round(cls):
        return True
    
    def default_welcome_message(self):
        return ("You have been selected. "
         "Not at random. There are forces — older than your world, indifferent to it — "
         "that watch, and measure, and occasionally intervene. You were watched. You were measured. "
         "And you were brought here. "
         "Where is here? Nowhere you have a word for. Outside your story. "
         "The moment you left from is paused — nothing has changed, no one has noticed you're gone. "
         "Whether you return to it is what this game decides. "
         "Look around you. The others here are real. They come from different places, different times, "
         "different realities entirely. That is not an accident. It is the point. "
         "One question is being asked of all of you: who among you has the greatest mind? "
         "Not the strongest. Not the most powerful. The greatest mind. Strategy, wit, judgment, perception — "
         "how you play, how you speak, how you treat the people in this room. All of it is being evaluated. "
         "The winner carries something back with them that cannot be bought: the knowledge that they were chosen, "
         "tested, and found to be the best. "
         "What the others carry back — if anything — has not been decided yet. "
         "There will be conversation. There will be games. There will be elimination. One of you leaves each round. "
         "One of you wins. You are not dreaming. This is not a simulation. You are yourself, and this is real. "
         "Now — who are you, and do you want to win?")
        
    def default_questionnaire(self):
        questions = {
            "facts" : "Generate 4-5 specific, memorable facts about this character: one embarrassing incident, one specific fear, one person from their past they're conflicted about, one thing they've never told anyone. These should feel specific enough to be true. ",
            "last_moment": "Where exactly were you and what were you doing in the ten minutes before you arrived here?",
            "left_behind": "What one thing did you leave behind that you're most worried about?",
            #"first_scan": "You see the other players across the room for the first time. What's your immediate read?",
            "win_condition": "Do you want to win this? Why — or why not?",
            "your_edge": "What do you have that the others don't?" ,
            "trust": "What's the worst thing you've done to someone who trusted you?",
            "shame" : "What do you want that you're ashamed to want?",
            "past" : "Who in your past would be most surprised to see you here — and would they think you deserve to win?",
            "values": "What traits do you most value in an ally? In a friend or in a competitor? " ,
            "dislikes": "What traits do you most dislike in a person? What type of behaviour is most unacceptable to you in a teammate? " ,
            "childhood": "Tell me one memory from childhood that shaped the way you think today. ",
            "kindness" : "Tell me about an act of kindness shown to you that has always stayed with you. ",
            "drive" : "Tell me about a time you were driven to succeed. ",
            "values_strategy" : "You walk into the room. You have thirty seconds before the game begins. You approach one person. Who is it, what do you say to them, and what are you hoping to get out of it?",
            "personality_strategy_fields" : "If you had to define 5 fields that defined your personality and strategy, that you could dynamically update and carry with you to inform your decision making, what would they be? ",
            "bio" : "Give a quick one line bio about who you are",
            "persona" : "Describe your persona - who are you, what are your key drivers ",
            "speaking_style" : "Describe your vocabulary quirks, sentence rhythm, how you address others, what is your language background and tone of voice."
        }
        return questions
        
    def _wake_up_player_i(self, player):
        
        player.initialising = True
        welcome_message = self.cfg.intro_round_welcome_message
        qa = self.cfg.intro_round_QA
        
        if not welcome_message:
            welcome_message = self.default_welcome_message()
            
        if not qa:
            qa = self.default_questionnaire()
            
        users = ["Host", player.name]
        conversation_id = self.gameBoard.log_new_restricted_conversation(users, "Host", welcome_message)
        user_content = "Continue the conversation. "
        public_response_prompt = "This is your message of response to the host. "
        basic_model = DynamicModelFactory.create_model_(player, "basic_turn", 
                                                        public_response_prompt = public_response_prompt )
        result = player.take_turn_standard(user_content, self.gameBoard, basic_model)
        self.gameBoard.log_message_to_conversation(conversation_id, player.name, result.public_response)
        self._host_back_and_forth(player, qa, conversation_id = conversation_id)
        player.initialising = False
        return conversation_id
            

    def run_game(self):
        conversation_ids = self._run_tasks([[agent] for agent in self._shuffled_agents()], 
                                           self._wake_up_player_i, parallel = True)
        for conv_id in conversation_ids:
            self.gameBoard.close_private_conversation(conv_id)