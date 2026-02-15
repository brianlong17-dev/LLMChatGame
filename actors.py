from abc import abstractmethod
from collections import deque
from prompts import PromptLibrary
from models import *

class GameMaster:
    def __init__(self, client, model_name: str):
        self.model_name = model_name
        self.client = client
        
    def summariseRound(self, gameBoard): 
        turn = self.client.create(
            model=self.model_name,
            response_model=SumariseRoundComplex,
            messages=[
                {"role": "system", "content": f"You over see this game. You help to make the information managable for the LLMs playing."},
                {"role": "user", "content": f"PAST SUMARRIES: {gameBoard.round_summaries} "
                 f"#########################"
                 f"Summarise the following round: {gameBoard.currentRound} Scores:  {gameBoard.agent_scores}"} 
            ]
        )
        return turn
        
    def compressRounds(self, rounds):
        return ("")
    


class BaseActor:
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str, color = "BLUE"):
        self.name = name
        self.persona = initial_persona
        self.client = client
        self.model_name = model_name
        self.form = initial_form
        self.life_lessons = deque(maxlen=6)
        self.color = color
    
    def isAgent(self):
        return False 
    
    def emptyResponses(self):
        return["", "none"]
    
    

class Debater(BaseActor):
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str):
        super().__init__(name, initial_persona, initial_form, client, model_name)
        self.rating = 0
        self.strategy_to_win = "WATCH AND UPDATE WITH A PLAN"
    
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
        
    def finalWords(self, gameBoard):
        system_content = PromptLibrary.agent_system(self, gameBoard)
        
        result = self.client.create(
                model=self.model_name,
                response_model=FinalWords,
                messages=[
                    {"role": "system", "content": f"You are {self.name}. You have been voted off."
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\n You have been voted out! What are you last words?"}
                ]
            )
        return result
    
    def voteOnePlayerOff(self, gameBoard, other_agent_names):
        system_content = PromptLibrary.agent_system(self, gameBoard)
        other_agents = [name for name in gameBoard.agent_names if name != self.name]
        
        vote_result = self.client.create(
                model=self.model_name,
                response_model=newAgentRemovalModel(other_agents),
                messages=[
                    {"role": "system", "content": f"You are {self.name}. Each player gets a vote. You must vote for one player you want to leave the completition. They player with the most votes will leave the game."
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\nWho do you vote to leave? Who do you eliminate from {other_agents} and why?"}
                ]
            )
        return vote_result
            
               
    def votePlayerOff(self, gameBoard):
        system_content = PromptLibrary.agent_system(self, gameBoard)
        other_agents = [name for name in gameBoard.agent_names if name != self.name]
        
        vote_result = self.client.create(
                model=self.model_name,
                response_model=newAgentRemovalModel(other_agents),
                messages=[
                    {"role": "system", "content": f"You are {self.name}. You have won the round. You must now eliminate one of your rival"
                     f"{system_content}"},
                    {"role": "user", "content": f"Context: {gameBoard.get_full_context()}\n\nWho do you eliminate from {other_agents} and why?"}
                ]
            )
        return vote_result
            

class Judge(BaseActor):
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str):
        super().__init__(name, initial_persona, initial_form, client, model_name)
        self.complex_persona = PromptLibrary.desc_judge_initialPersona
        self.color = "RED"
        self.judgingCriteria = "Building connections, answering questions, and creating compelling storylines"
        self.canUpdateJudgingCiteria = True
        
    def take_turn(self, gameBoard) -> dict:
        system_content = PromptLibrary.judge_system(self, gameBoard)
        user_content = PromptLibrary.judge_user(self, gameBoard) 
        turn: JudgeTurn = self.client.create(
            model=self.model_name,
            response_model=JudgeTurn,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
        )
        self.complex_persona = turn.complex_persona
        if turn.judgingCriteria and self.canUpdateJudgingCiteria:
            print(f"⚖️ NEW CRITERIA: {turn.judgingCriteria}")
            self.judgingCriteria = turn.judgingCriteria
            
        if turn.lifeLesson != "":
            self.life_lessons.append(turn.lifeLesson)
        
        gameBoard.updateFromJudgement(turn)
        public_text = f"[{turn.public_action}]\n {turn.public_response}"
        private_data = {
            "internal_monologue": turn.internal_monologue,
            "new_persona": turn.complex_persona
        }
        
        creation_request = None #self.create_new_agent_turn() if turn.create_new_agent else None
        kill_request = None
        
        
        if turn.create_new_agent:
            creation_request = self.create_new_agent(gameBoard, turn)
            public_text += (f"\n {creation_request.public_response}")
            private_data["creation_thought_process"] = creation_request.thought_process
            private_data["creation_internal_monologue"] = creation_request.internal_monologue
            
        if turn.remove_agent:
            kill_request = self.remove_agent(gameBoard, turn)
            print(kill_request)
            public_text += (f"\n {kill_request.public_response}")
            private_data["kill_thought_process"] = kill_request.thought_process
            private_data["kill_internal_monologue"] = kill_request.internal_monologue
        
        ejection_target =  kill_request.name if  kill_request != None else None
        
        return {
            "turn": turn,
            "public_text": public_text,
            "private_text" : private_data,
            "creation_turn" : creation_request,
            "ejection_target": ejection_target
        }

    def remove_agent(self, game_board, turn) -> dict:
        """Called when the Narrator intervenes."""
        history = game_board.get_full_context()
        names = game_board.agent_names
        print(game_board.agent_names)
        turn = self.client.create(
            model=self.model_name,
            response_model=newAgentRemovalModel(names),
            messages=[
                {"role": "system", "content": f"You are {PromptLibrary.judgeName}. You are killing a new player because you have decided to "
                 "This is the recent history: {history}"},
                {"role": "user", "content": f"This is the information of your previous turn: {turn}: "}
            ]
        )
        return turn
        
    def create_new_agent(self, game_board, turn) -> dict:
        """Called when the Narrator intervenes."""
        history = game_board.get_full_context()
        turn = self.client.create(
            model=self.model_name,
            response_model=NewAgentManifest,
            messages=[
                {"role": "system", "content": f"You are {PromptLibrary.judgeName}. You are creating a new player because you have decided to "
                 "This is the recent history: {history}"},
                {f"role": "user", "content": "This is the information of your previous turn: {turn} "} 
            ]
        )
        return turn
        #self.persona = turn.updated_persona_summary
        
        
