from .actors import BaseActor
from prompts.prompts import PromptLibrary
from models.player_models import JudgeTurn, NewAgentManifest, DynamicModelFactory

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
            response_model=DynamicModelFactory.choose_agent_to_remove_model(names),
            messages=[
                {"role": "system", "content": f"You are {PromptLibrary.judgeName}. You are killing a new player because you have decided to This is the recent history: {history}"},
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
                              f"This is the recent history: {history}"},
                {"role": "user", "content": f"This is the information of your previous turn: {turn} "}
            ]
        )
        return turn
        #self.persona = turn.updated_persona_summary
        
        
