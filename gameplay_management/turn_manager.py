from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional
from pydantic import Field, create_model
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary

if TYPE_CHECKING:
    from agents.player import Debater
    from gameplay_management.base_manager import BaseRound


class TurnManager:

    def __init__(self, base_manager: 'BaseRound'):
        self.base_manager = base_manager
        self._buffer_amount = 0.6 #default
        self.optional_responses_in_use = False

    @property
    def gameBoard(self):
        return self.base_manager.gameBoard

    # --- Model Creation ---

    def _make_model_optional(self, model, agent):
        buffer = agent.optional_response_buffer

        existing_thought_desc = model.model_fields["private_thoughts"].description or ""
        updated_thought_desc = existing_thought_desc + f" Note: this turn has optional public response — responding costs 1 buffer point. Your buffer: {buffer}. Will you spend it here, or save it for later? "

        existing_response_desc = model.model_fields["public_response"].description or ""
        updated_response_desc = existing_response_desc + f" Your optional response buffer is at: {buffer}. If you want to save it for later: Return null — do not write anything here, do not explain your choice or silence. "

        return create_model(
            model.__name__,
            __base__=model,
            private_thoughts=(str, Field(description=updated_thought_desc)),
            public_response=(Optional[str], Field(default=None, description=updated_response_desc))
        )

    def _create_response_model(self,
                               player,
                               model_name: str = "DynamicTurnModel",
                               public_response_prompt = None,
                               private_thoughts_prompt = None,
                               additional_thought_nudge = None,
                               action_fields = None,
                               game_logic_fields = None):
        return DynamicModelFactory.create_model_(
            player,
            model_name,
            public_response_prompt=public_response_prompt,
            private_thoughts_prompt=private_thoughts_prompt,
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields,
            game_logic_fields=game_logic_fields
        )

    # --- Field Builders ---

    def create_choice_field(self, field_name, choices, field_description = None):
        if not field_description:
            field_description = "Your final choice."
        choice_definition = (Literal[*choices], Field(description=field_description))
        return {field_name: choice_definition}

    def create_basic_field(self, field_name, field_description):
        field_definition = (str, Field(description=field_description))
        return {field_name: field_definition}

    def _choose_name_field(self, allowed_names, reason_for_choosing_prompt, field_name = None):
        if not field_name:
            field_name = GamePromptLibrary.model_field_choose_name
        choice_reason_prompt = f"The exact name of the agent. {reason_for_choosing_prompt}"
        return self.create_choice_field(field_name, allowed_names, choice_reason_prompt)

    # --- Turn Execution ---

    def take_turn(self, player, user_content, *,
                  model_name: str = "DynamicTurnModel",
                  public_response_prompt: str = None,
                  private_thoughts_prompt: str = None,
                  additional_thought_nudge: str = None,
                  action_fields = None,
                  game_logic_fields = None,
                  instruction_override = None,
                  optional: bool = False,
                  broadcast: bool = False):
        
        
        optional = optional and self.optional_responses_in_use
        if optional:
            additional_thought_nudge = additional_thought_nudge or "Is this a worthwile place to spend your optional response buffer? Why?"
            speak_silent_field = self.create_choice_field(
                "will_you_speak_or_remain_silent",
                ["speak", "remain_silent"],
                "Declare your choice first. If 'remain_silent', leave public_response null."
            )
            game_logic_fields = {**(game_logic_fields or {}), **speak_silent_field}

        model = self._create_response_model(
            player,
            model_name,
            public_response_prompt=public_response_prompt,
            private_thoughts_prompt=private_thoughts_prompt,
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields,
            game_logic_fields=game_logic_fields
        )

        if optional:
            result = self._basic_turn_optional(model, player, user_content)
        else:
            result = player.take_turn_standard(user_content, self.gameBoard, model, instruction_override=instruction_override)

        if broadcast and result and result.public_response:
            self.gameBoard.handle_public_private_output(player, result)

        return result

    def respond_to(self, player: Debater, text_to_respond_to: str, public_response_prompt: str = None,
                   private_thoughts_prompt: str = None, instruction_override = None):
        return self.take_turn(player, text_to_respond_to,
                              public_response_prompt=public_response_prompt,
                              private_thoughts_prompt=private_thoughts_prompt,
                              instruction_override=instruction_override)

    def get_response(self, player, model_name, context_msg, action_fields = None, additional_thought_nudge = None):
        return self.take_turn(player, context_msg,
                              model_name=model_name,
                              additional_thought_nudge=additional_thought_nudge,
                              action_fields=action_fields)

    def _ask_directed_question(self, player, possible_target_names, user_content,
                               public_response_prompt, additional_thought_nudge = None):
        action_fields = self._choose_name_field(possible_target_names, "Who your question/statement is directed to. ")
        return self.take_turn(player, user_content,
                              public_response_prompt=public_response_prompt,
                              additional_thought_nudge=additional_thought_nudge,
                              action_fields=action_fields,
                              broadcast=True)

    def _basic_turn(self, agent, user_content_prompt, public_response_prompt,
                    private_thoughts_prompt = None, optional = False):
        return self.take_turn(agent, user_content_prompt,
                              model_name="basic_turn",
                              public_response_prompt=public_response_prompt,
                              private_thoughts_prompt=private_thoughts_prompt,
                              optional=optional,
                              broadcast=True)

    # --- Optional Response Mechanics ---

    def _basic_turn_optional(self, model, agent, user_content_prompt):
        agent.optional_response_buffer = round(agent.optional_response_buffer + self._buffer_amount, 2)
        if agent.optional_response_buffer < 1:
            self._low_buffer_message(agent)
            return None

        model = self._make_model_optional(model, agent)
        optional_response_prompt = (f"Optional turn. Your buffer auto-grows by {self._buffer_amount} every optional turn whether you speak or stay silent. "
            f"Speaking additionally costs 1 unit. Your current buffer: {agent.optional_response_buffer}. "
            f"Staying silent is free and lets the buffer accumulate for higher-value moments later.")
        user_content_prompt += f"\n{optional_response_prompt}\n"

        result = agent.take_turn_standard(user_content_prompt, self.gameBoard, model)
        if result.public_response:
            agent.optional_response_buffer = round(agent.optional_response_buffer - 1, 2)
            self.base_manager.debug_print(f"{agent.name} spends buffer - new buffer: {agent.optional_response_buffer} ")
        else:
            self.base_manager.debug_print(f"{agent.name} passes, buffer: {agent.optional_response_buffer}")
            self.base_manager.debug_print(f"{agent.name} thoughts: {result.private_thoughts}")
        return result

    def _low_buffer_message(self, agent):
        self.base_manager.private_system_message(agent, "Your turn here was passed as your optional response buffer was too low.")
