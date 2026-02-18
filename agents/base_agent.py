from abc import abstractmethod
from collections import deque

class BaseAgent:
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
   
   


 
