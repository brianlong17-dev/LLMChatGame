from prompts.prompts import PromptLibrary
from models import *
from agents.actors import BaseActor


class Debater(BaseActor):
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str):
        super().__init__(name, initial_persona, initial_form, client, model_name)
        self.rating = 0
        self.strategy_to_win = "WATCH AND UPDATE WITH A PLAN"
        #todo : implement temperature
    
    def isAgent(self):
        return True
    
   
        
    
    def take_turn(self, gameBoard):
    #history_context: str, judge_persona: str, scores: dict[str, int], forms: dict[str, str]) -> dict:
        system_content = PromptLibrary.agent_system(self, gameBoard)
        user_content =PromptLibrary.agent_prompt(self.life_lessons, gameBoard.get_full_context())
        turn: AgentTurn = self.client.create(
            model=self.model_name,
            response_model=AgentTurn,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
        )
        self.persona = turn.updated_persona_summary
        if turn.updated_strategy_to_win.lower() not in self.emptyResponses():
            self.strategy_to_win = turn.updated_strategy_to_win 
        
        private_data = {
            "internal_monologue": turn.internal_monologue,
            "new_persona": turn.updated_persona_summary,
            "strategy_to_win": {self.strategy_to_win}
        }
        if turn.lifeLesson != "" and turn.lifeLesson not in self.life_lessons:
            self.life_lessons.append(turn.lifeLesson)
        return {
            "turn": turn,
            "public_text": f"[{turn.public_action}]\n {turn.public_response}",
            "private_text" : private_data
        }
    
    def splitOrSteal(self, gameBoard, opponent_agent):
        system_content = PromptLibrary.agent_system(self, gameBoard)
        splitPoints = PromptLibrary.pd_split
        stealPoints = PromptLibrary.pd_steal
        bothSteal = PromptLibrary.pd_both_steal
        promptMessage = (
            f"🚨 PRISONER'S DILEMMA 🚨\n"
            f"You have been paired with {opponent_agent.name}.\n"
            f"Remember:\n"
            f"- If you both SPLIT, you both get {splitPoints} points.\n"
            f"- If you STEAL and they SPLIT, you get {stealPoints} points and they get 0.\n"
            f"- If you both STEAL, you both get {bothSteal} point.\n"
            f"Based on your game history and personality, make your choice."
        )
        result = self.client.create(
                model=self.model_name,
                response_model=DynamicModelFactory.prisoners_dilemma_model(),
                messages=[
                    {"role": "system", "content": f"You are {self.name}."
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\n {promptMessage}"}
                ]
            )
        return result
    
    
    def respond_to(self, gameBoard, event_message):
        """
        A flexible method for the agent to react to system announcements or specific events.
        """
        prompt = (
            f"The system has just announced the following:\n"
            f"'{event_message}'\n\n"
            f"Provide your reaction to this event."
        )

        messages = [
            {"role": "system", "content": PromptLibrary.agent_system(self, gameBoard)},
            {"role": "user", "content": prompt}
        ]

        response = self.client.create(
            model=self.model_name,
            response_model=AgentReaction,
            messages=messages
        )
        
        return response
    
    def finalWords(self, gameBoard):
        "this should be replaced with a generic respond"
        system_content = PromptLibrary.agent_system(self, gameBoard)
        
        result = self.client.create(
                model=self.model_name,
                response_model=DynamicModelFactory.basic_turn_model("final_words_model") ,
                messages=[
                    {"role": "system", "content": f"You are {self.name}. You have been voted off."
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\n You have been voted out! What are you last words?"}
                ]
            )
        return result
    
    def voteOnePlayerOff(self, gameBoard, other_agent_names):
        system_content = PromptLibrary.agent_system(self, gameBoard)
        
        vote_result = self.client.create(
                model=self.model_name,
                response_model=DynamicModelFactory.choose_agent_to_remove_model(other_agent_names),
                messages=[
                    {"role": "system", "content": f"You are {self.name}. Each player gets a vote. You must vote for one player you want to leave the competition. They player with the most votes will leave the game."
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\nWho do you vote to leave? Who do you eliminate from {other_agent_names} and why?"}
                ]
            )
        return vote_result
            
               
    def votePlayerOff(self, gameBoard):
        system_content = PromptLibrary.agent_system(self, gameBoard)
        other_agents = [name for name in gameBoard.agent_names if name != self.name]
        
        vote_result = self.client.create(
                model=self.model_name,
                response_model=DynamicModelFactory.choose_agent_to_remove_model(other_agents),
                messages=[
                    {"role": "system", "content": f"You are {self.name}. You have won the round. You must now eliminate one of your rivals"
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\nWho do you eliminate from {other_agents} and why?"}
                ]
            )
        return vote_result
          