from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional
from pydantic import Field, create_model
from agents.player_response_models import AgentResponseModelFactory

if TYPE_CHECKING:
    from agents.abstract_agentic_player import AbstractAgenticPlayer
    from gameplay_management.base_manager import BaseRound



class TurnManager:

    def __init__(self, base_manager: 'BaseRound'):
        self.base_manager = base_manager
        self._buffer_amount = 0.6 #default
        self.optional_responses_in_use = False

    @property
    def game_board(self):
        return self.base_manager.game_board

    # --- Model Creation ---
    
    def _get_target_name_from_response(self, response):
        return getattr(response, self.base_manager.TARGET_NAME_FIELD, None)

    def _make_model_optional(self, model, agent):
        #raise Exception("This needs to be turned on in player_system_prompt(cls, agent, include_optional_response = False)")

        if agent.is_human():
            #TODO this needs to be sent to the human via response description
            return model
        
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

    # --- Field Builders ---

    def create_choice_field(self, field_name, choices, field_description = None):
        if not field_description:
            field_description = "Your final choice."
        choice_definition = (Literal[*choices], Field(description=field_description))
        return {field_name: choice_definition}

    def create_basic_field(self, field_name, field_description, optional: bool = False):
        if optional:
            field_definition = (Optional[str], Field(default=None, description=field_description))
        else:
            field_definition = (str, Field(description=field_description))
        return {field_name: field_definition}

    def _choose_name_field(self, allowed_names, reason_for_choosing_prompt, field_name = None):
        if not field_name:
            field_name = self.base_manager.TARGET_NAME_FIELD
        choice_reason_prompt = f"{reason_for_choosing_prompt}"
        return self.create_choice_field(field_name, allowed_names, choice_reason_prompt)

    # --- Turn Execution ---
    
    def take_turn_optional(self, player, turn_prompt, *,
                  model_name: str = "DynamicTurnModel",
                  public_response_prompt: str = None,
                  private_thoughts_prompt: str = None,
                  additional_thought_nudge: str = None,
                  action_fields = None,
                  game_logic_fields = None,
                  action_post_response: bool = False,
                  broadcast: bool = False,
                  is_reply = False,
                  use_higher_model=False):
        #if not self.optional_responses_in_use: should be handled oustside of here maybe?

        additional_thought_nudge = additional_thought_nudge or "Is this a worthwile place to spend your optional response buffer? Why?"
        speak_silent_field = self.create_choice_field(
            "will_you_speak_or_remain_silent",
            ["speak", "remain_silent"],
            "Declare your choice first. If 'remain_silent', leave public_response null."
        )
        game_logic_fields = {**(game_logic_fields or {}), **speak_silent_field}

        model = self._create_model(
            player,
            model_name,
            public_response_prompt=public_response_prompt,
            private_thoughts_prompt=private_thoughts_prompt,
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields,
            game_logic_fields=game_logic_fields,
            action_post_response=action_post_response,
        )

        result = self._basic_turn_optional(model, player, turn_prompt, use_higher_model=use_higher_model)
        if broadcast and result and result.public_response:
            self._output_response(player, result, is_reply=is_reply)
        return result


    def take_turn(self, player, turn_prompt, *,
                  model_name: str = "DynamicTurnModel",
                  public_response_prompt: str = None,
                  private_thoughts_prompt: str = None,
                  additional_thought_nudge: str = None,
                  action_fields = None,
                  game_logic_fields = None,
                  action_post_response: bool = False,
                  instruction_override = None,
                  broadcast: bool = False,
                  is_reply = False,
                  speech=False,
                  thinking = False,
                  use_higher_model=False,
                  multi_answer_model=False,
                  human_input_description_object=None):

        model = self._create_model(
            player,
            model_name,
            public_response_prompt=public_response_prompt,
            private_thoughts_prompt=private_thoughts_prompt,
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields,
            game_logic_fields=game_logic_fields,
            action_post_response=action_post_response,
            multi_answer_model=multi_answer_model,
            speech=speech
        )

        result = player.take_turn_standard(turn_prompt, self.game_board, model, instruction_override=instruction_override, thinking=thinking,
                                               use_higher_model=use_higher_model,
                                               human_input_description_object=human_input_description_object)
        if broadcast:
            self._output_response(player, result, is_reply=is_reply)
        return result

    def _create_model(
            self,
            player,
            model_name: str = "DynamicTurnModel",
            public_response_prompt: str = None,
            private_thoughts_prompt: str = None,
            additional_thought_nudge: str = None,
            action_fields = None,
            game_logic_fields = None,
            action_post_response: bool = False,
            multi_answer_model=False,
            speech=False
        ):
        model = AgentResponseModelFactory.create_model_(
            player,
            game_board=self.game_board,
            model_name=model_name,
            public_response_prompt=public_response_prompt,
            private_thoughts_prompt=private_thoughts_prompt,
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields,
            game_logic_fields=game_logic_fields,
            action_post_response=action_post_response,
            mobile_outputs=self.game_board.mobile_outputs,
            multi_answer_model=multi_answer_model,
            speech=speech)
        return model
                      
    def respond_to(self, player: AbstractAgenticPlayer, turn_prompt: str, public_response_prompt: str = None,
                   private_thoughts_prompt: str = None, additional_thought_prompt: str = None, instruction_override = None, broadcast = True, is_reply = False,
                   prefix_turn_prompt: bool = True, human_input_description_object = None):

        if prefix_turn_prompt:
            turn_prompt = f"Respond to: \n{turn_prompt}"
        return self.take_turn(player, turn_prompt,
                              public_response_prompt=public_response_prompt,
                              private_thoughts_prompt=private_thoughts_prompt,
                              instruction_override=instruction_override,
                              additional_thought_nudge=additional_thought_prompt,
                              broadcast = broadcast,
                              is_reply = is_reply,
                              human_input_description_object=human_input_description_object)

    def _ask_directed_question(self, player, possible_target_names, turn_prompt,
                               public_response_prompt, additional_thought_nudge = None, is_reply = False,
                               human_input_description_object = None):
        target_field_description = "Direct a question or address the group.  "
        response = self._targeted_turn(player, possible_target_names, target_field_description, turn_prompt,
                               public_response_prompt, additional_thought_nudge, broadcast=False,
                               human_input_description_object=human_input_description_object)
        self._output_response(player, response, include_target_name=True, is_reply=is_reply)
        return response

    def _targeted_turn(self, player, possible_target_names, target_field_description, turn_prompt,
                               public_response_prompt, additional_thought_nudge = None, broadcast = False,
                               include_target_name = False, is_reply = False,
                               human_input_description_object = None):
        action_fields = self._choose_name_field(possible_target_names, target_field_description)
        return self.take_turn(player, turn_prompt,
                              public_response_prompt=public_response_prompt,
                              additional_thought_nudge=additional_thought_nudge,
                              action_fields=action_fields,
                              broadcast=broadcast,
                              is_reply = is_reply,
                              human_input_description_object=human_input_description_object)
        
    def _basic_turn(self, agent, turn_prompt, public_response_prompt,
                    private_thoughts_prompt = None):
        return self.take_turn(agent, turn_prompt,
                              model_name="basic_turn",
                              public_response_prompt=public_response_prompt,
                              private_thoughts_prompt=private_thoughts_prompt,
                              broadcast=True)

    # --- Optional Response Mechanics ---

    def _basic_turn_optional(self, model, agent, turn_prompt, use_higher_model=False):
        agent.optional_response_buffer = round(agent.optional_response_buffer + self._buffer_amount, 2)
        if agent.optional_response_buffer < 1:
            self._low_buffer_message(agent)
            return None

        model = self._make_model_optional(model, agent)
        optional_response_prompt = (f"Optional turn. Your buffer auto-grows by {self._buffer_amount} every optional turn whether you speak or stay silent. "
            f"Speaking additionally costs 1 unit. Your current buffer: {agent.optional_response_buffer}. "
            f"Staying silent is free and lets the buffer accumulate for higher-value moments later.")
        turn_prompt += f"\n{optional_response_prompt}\n"

        result = agent.take_turn_standard(turn_prompt, self.game_board, model, use_higher_model=use_higher_model)
        if result.public_response:
            agent.optional_response_buffer = round(agent.optional_response_buffer - 1, 2)
            self.base_manager.debug_print(f"{agent.name} spends buffer - new buffer: {agent.optional_response_buffer} ")
        else:
            self.base_manager.debug_print(f"{agent.name} passes, buffer: {agent.optional_response_buffer}")
            if not agent.is_human():
                self.base_manager.debug_print(f"{agent.name} thoughts: {result.private_thoughts}")
        return result
        
    def _low_buffer_message(self, agent):
        self.base_manager.private_system_message(agent, "Your turn here was passed as your optional response buffer was too low.")

    # --- Output --- #

    def _format_public_response(self, response, pre_message_choice_reveal=None, post_message_choice_reveal=None, include_target_name=False):
        public_response = response.public_response
        pre_string = None
        post_string = None
        
        if pre_message_choice_reveal:
            choice_value = getattr(response, pre_message_choice_reveal, None)
            if choice_value is not None:
                pre_string = f"*{str(choice_value).upper()}*"
        if post_message_choice_reveal:
            choice_value = getattr(response, post_message_choice_reveal, None)
            if choice_value is not None:
                post_string = f"*{str(choice_value).upper()}*"
    
        if pre_string:
            public_response = f"{pre_string}\n{public_response}"
        if post_string:
            public_response = f"{public_response}\n{post_string}"
            
        directed_to_name = None
        if include_target_name:
            directed_to_name = self._get_target_name_from_response(response)
            directed_to_name = None if directed_to_name == 'Group' else directed_to_name
        return public_response, directed_to_name

    def _output_response(self, player, response, single_message_overwrite=None, pre_message_choice_reveal=None, post_message_choice_reveal=None, is_reply=False, delay=0,
                         include_target_name=False, widget=None):

        if single_message_overwrite:
            #In case of multiple turns being included in a single response model- we will only have public output.
            return self.game_board.broadcast_public_action_agent(player, single_message_overwrite, is_reply=is_reply, delay=delay, widget=widget)

        private_thoughts = None if player.is_human() else getattr(response, 'private_thoughts', None)
        private_thoughts_brief = None if player.is_human() else getattr(response, 'private_thoughts_brief', None)
        public_response, directed_to_name = self._format_public_response(response, pre_message_choice_reveal, post_message_choice_reveal, include_target_name)
        self.game_board.handle_public_private_output(player,
                public_response, private_thoughts, private_thoughts_brief, delay=delay,
                is_reply=is_reply, directed_to_name=directed_to_name, widget=widget)
