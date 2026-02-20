from collections import deque
from abc import ABC, abstractmethod

class BaseAgent:
    def __init__(self, name: str, initial_persona: str, initial_form: str,client, model_name: str, color = "BLUE"):
        self.name = name
        self.persona = initial_persona
        self.client = client
        self.model_name = model_name
        self.form = initial_form
        self.life_lessons = deque(maxlen=6)
        self.color = color
    
    
    def lazy_responses(self):
        return{"", "none", " ", "n/a", "not applicable", "nothing", "no lesson"}
    
    @abstractmethod
    def _system_prompt(self, gameBoard):
        raise NotImplementedError("Subclasses must implement _system_prompt!")
    
    def get_response(self,  user_content, response_model, gameBoard, system_content = None):
        
        if system_content is None:
            system_content = self._system_prompt(gameBoard)
            
        messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
        
        response = self.client.create(
            model=self.model_name,
            response_model=response_model,
            messages=messages
        )
        return response
   
   


 
