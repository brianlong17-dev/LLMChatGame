from collections import deque
from pydantic import Field, ValidationError
from agents.player import Debater
from typing import get_args, get_origin, Literal
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from gameplay_management import *

class Human(Debater):
    
    
    def __init__(self, name: str):
        super().__init__(name = name, initial_persona= '', client = None, model_name = None,
                         higher_model_name= None, speaking_style = "")
        self.is_testing = True
    
    def is_human(self):
        return True
    
    def get_response(self, user_content: str, response_model, gameBoard, system_content: str = None):
        system_content = system_content or self._system_prompt(gameBoard)
        if self.is_testing:
            print(f"[GAME STATE]:\n{system_content}")
            print(f"[PROMPT]:\n{user_content}")
            print("-" * 50)

        fields = response_model.model_fields
        while True:
            answers = self._collect_answers(fields, gameBoard)
            try:
                return response_model(**answers)
            except ValidationError as e:
                self._handle_validation_error(e, gameBoard.game_sink)

    
    def _collect_answers(self, fields: dict, gameBoard) -> dict:
        answers = {}
        for field_name, field_info in fields.items():
            if field_name == "private_thoughts":
                answers[field_name] = ""
                continue
            answers[field_name] = self._prompt_field(field_name, field_info, gameBoard)
        return answers

    def _prompt_field(self, field_name: str, field_info, gameBoard) -> str:
        description = field_info.description or f"Enter value for {field_name}"
        annotation = field_info.annotation
        if get_origin(annotation) is Literal:
            choices = [str(a) for a in get_args(annotation)]
            return gameBoard.game_sink.get_user_input_multiple_choice(field_name, description, choices)
        return gameBoard.game_sink.get_user_input_simple(field_name, description)

    def _handle_validation_error(self, e: ValidationError, gameBoard):
        gameBoard.game_sink.system_private("❌ FORMAT ERROR: The game engine rejected your input.")
        for error in e.errors():
            gameBoard.game_sink.system_private(f" - Field '{error['loc'][0]}': {error['msg']}")
        gameBoard.game_sink.system_private("Let's try that again...\n")

        