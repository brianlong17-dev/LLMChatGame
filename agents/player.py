from prompts.gamePrompts import GamePromptLibrary
from prompts.prompts import PromptLibrary
from models import *
from agents.base_agent import BaseAgent
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gamplay_management import *

class Debater(BaseAgent):
    
    
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str):
        super().__init__(name, initial_persona, initial_form, client, model_name)
        self.rating = 0
        self.strategy_to_win = "WATCH AND UPDATE WITH A PLAN"
        self.mathematicalAssessment = ""
        #todo : implement temperature
    
    def _system_prompt(self, gameBoard):
        return PromptLibrary.player_system_prompt(self, gameBoard)
    
    
    def _check_if_empty(self, text: str):
        if not text:
            return True
        clean_text = text.strip().rstrip('.').lower()
        lazy_responses = self.lazy_responses() 
        
        return clean_text in lazy_responses
        
    def process_turn_complex_fields(self, turn):
        #if they have used a complex model, we want to process those fields
        
        updated_persona_summary = getattr(turn, "updated_persona_summary", None)
        if updated_persona_summary:
            self.persona = turn.updated_persona_summary
        
        updated_strategy_to_win = getattr(turn, "updated_strategy_to_win", None)
        if updated_strategy_to_win and not self._check_if_empty(turn.updated_strategy_to_win):
            self.strategy_to_win = turn.updated_strategy_to_win 
                
        lifeLesson = getattr(turn, "lifeLesson", None)
        if lifeLesson:     
            if not self._check_if_empty(turn.lifeLesson.lower()) and turn.lifeLesson not in self.life_lessons:
                #TODO prob should clean this before checking if it already is
                self.life_lessons.append(turn.lifeLesson)
               
        mathematicalAssessment = getattr(turn, "mathematicalAssessment", None)
        if not self._check_if_empty(turn.mathematicalAssessment):
            self.mathematicalAssessment = turn.mathematicalAssessment 
    
    def _get_full_user_content(self, gameBoard, user_content):
        
        full_user_content= f"{PromptLibrary.player_user_prompt(list(self.life_lessons), gameBoard.get_full_context())}\n{user_content}"
        return full_user_content
                     
    def take_turn_standard(self, user_content, gameBoard, model, system_content = None, append_complex_fields = True):
        #Human player split will be here---- needing to demark the required fields is the question.
        #it is only public words and action, and anyway, public words isnt even required.
        if append_complex_fields:
            model = DynamicModelFactory.with_complex_fields(model)
        user_content = self._get_full_user_content(gameBoard, user_content)
        turn = self.get_response(user_content, model, gameBoard, system_content)
        self.process_turn_complex_fields(turn)
        return turn
        
        
    def make_discussion_turn(self, gameBoard):
        user_content = PromptLibrary.player_user_prompt(list(self.life_lessons), gameBoard.get_full_context())
        basic_model = DynamicModelFactory.basic_turn_model("basic_turn")
        complex_model = DynamicModelFactory.with_complex_fields(basic_model)
        return self.take_turn_standard(user_content, gameBoard, complex_model)
    
    def choose_player_to_send_home(self, gameBoard, allowed_names, user_content):
        return self.take_turn_standard(user_content, gameBoard, DynamicModelFactory.choose_name_model(allowed_names, user_content))
    
    def choose_other_player(self, gameBoard, user_prompt, name_field_prompt = "", additional_thought_nudge = None):
        other_agent_names = [name for name in gameBoard.agent_names if name != self.name]
        response_model = DynamicModelFactory.choose_name_model(other_agent_names, name_field_prompt, additional_thought_nudge= additional_thought_nudge)
        return self.take_turn_standard(user_prompt, gameBoard, response_model)
    
    
    def choose_partner(self, gameBoard, allowed_names):
        user_content = (
            f"You get to choose who you want to play with from the following list: {allowed_names}.\n"
            f"Based on your history and the current game context, who do you choose to partner up with for the next mini-game and why?"
        )
        name_field_prompt = "The exact name of the agent to PAIR UP WITH.."
        response_model = DynamicModelFactory.choose_name_model(allowed_names, name_field_prompt)
        return self.take_turn_standard(user_content,gameBoard, response_model)
    

    def split_or_steal(self, gameBoard, opponent_agent):
        user_content = (
            f"🚨 PRISONER'S DILEMMA 🚨\n"
            f"You have been paired with {opponent_agent.name}.\n"
            f"Remember:\n"
            f"- If you both SPLIT, you both get {GamePromptLibrary.pd_split} points.\n"
            f"- If you STEAL and they SPLIT, you get {GamePromptLibrary.pd_steal} points and they get 0.\n"
            f"- If you both STEAL, you both get {GamePromptLibrary.pd_both_steal} point.\n"
            f"Based on your game history and personality, make your choice."
        )
        return self.take_turn_standard(user_content, gameBoard, DynamicModelFactory.prisoners_dilemma_model())
        
    def respond_to(self, gameBoard, event_message, public_response_prompt = None, private_thoughts_prompt = None):
        prompt = (
            f"So, this just happened! What do you want to say in response??:\n"
            f"'{event_message}'\n\n"
            f"Provide your reaction to this event."
        )
        model = DynamicModelFactory.basic_turn_model(public_response_prompt = public_response_prompt, 
                                                     private_thoughts_prompt = private_thoughts_prompt)
        return self.take_turn_standard(prompt, gameBoard, model)
     
    def finalWords(self, gameBoard):
        #This is a model about injecting specific field prompts
        #Is it needed? Debatable... Probably the sender should be giving these directly, in the respond to method, and then it
        #should be passed as **fields
        
        private_thoughts_prompt = "HOW DO YOU FEEL? What do you think but wouldn't say? What are you privately thinking?"
        public_response_prompt = "YOU ARE ABOUT TO DIE. What are you final words to the players?"
        response_model =  DynamicModelFactory.basic_turn_model("final_words", public_response_prompt = public_response_prompt, private_thoughts_prompt = private_thoughts_prompt)
        user_content = f"Context: {gameBoard.get_full_context()}\n\n You have been voted out! What are you last words?"
        return self.take_turn_standard(user_content, gameBoard, response_model)
        
    
    def voteOnePlayerOff(self, gameBoard, other_agent_names):
        system_content = PromptLibrary.player_system_prompt(self, gameBoard)
        
        vote_result = self.client.create(
                model=self.model_name,
                response_model=DynamicModelFactory.choose_agent_to_remove_model(other_agent_names),
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": (f"You are {self.name}. Each player gets a vote. You must vote for one player you want to leave the competition. They player with the most votes will leave the game."
                     f"Context: {gameBoard.get_full_context()}\n\nWho do you vote to leave? Who do you eliminate from {other_agent_names} and why?")}
                ]
            )
        return vote_result
            