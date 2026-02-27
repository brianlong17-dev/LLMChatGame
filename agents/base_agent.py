from collections import deque
from abc import ABC, abstractmethod

class BaseAgent:
    def __init__(self, name: str, client, model_name: str, higher_model_name: str = None, color = "BLUE"):
        self.name = name
        #self.persona = initial_persona
        self.client = client
        self.model_name = model_name
        self.higher_model_name = higher_model_name or model_name
        #self.form = initial_form
        self.color = color
    
    
    def lazy_responses(self):
        return{"", "none", " ", "n/a", "not applicable", "nothing", "no lesson"}
    
    @abstractmethod
    def _system_prompt(self, gameBoard):
        raise NotImplementedError("Subclasses must implement _system_prompt!")
    
    def get_response(self,  user_content: str, response_model, gameBoard, system_content: str = None):
        
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
   
   


 
