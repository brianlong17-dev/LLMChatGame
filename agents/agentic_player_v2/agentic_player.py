import re
from collections import deque
from pydantic import Field
from agents.agentic_player_v2.system_prompt import SystemPrompt
from core.game_context.user_content import UserContent
from core.game_context.summaries_builder import SummariesStringBuilder
from agents.player_response_models import AgentResponseModelFactory
from agents.base_agent import BaseAgent
from agents.abstract_agentic_player import AbstractAgenticPlayer
from typing import TYPE_CHECKING, Dict, Optional
if TYPE_CHECKING:
    from gameplay_management import *

class AgenticPlayer(AbstractAgenticPlayer):


    def __init__(self, name: str, initial_persona: str, api_client, speaking_style: str = ""):
        super().__init__(name, initial_persona, api_client=api_client, speaking_style=speaking_style)
        self.game_strategy = "Begin to take action and form strategy."
        self.life_lessons = deque(maxlen=8)
        self.phase_summaries_detailed = {}
        self.phase_summaries_brief = {}
        
        self.optional_response_buffer = 0
        
        
        self.character_dictionary = {}
        # -- State flags -- #
        self.game_over = False
        self.initialising = False
        self.currently_summarising = False
        self._mask_drop=False
        
        self.character_strategy = None
        self.emotional_state = None

        #persona
        self.initial_persona = initial_persona
        self.additional_persona_coloring = None
        self.persona_unique_detail = None
        
        #Speaking style
        self.initial_speaking_style = speaking_style
        self.speaking_style_update = None
        
    
    def uses_character_dictionary(self):
        return True

    def process_character_impressions(self, response):
        fields = [f for f in response.model_fields if f.startswith("impression_")]
        for field in fields:
            value = getattr(response, field)
            if value is not None:
                self.character_dictionary[field] = value
        for field in list(self.character_dictionary):
            if field not in fields:
                del self.character_dictionary[field]

    def _system_prompt_class(self):
        return SystemPrompt

    #def _get_full_user_content(): Implemented on AbstractAgenticPlayer

    #def take_turn_standard(): Implemented on AbstractAgenticPlayer

    def _process_standard_turn_response(self, response):
        self.process_evolution_fields(response)
        self.process_character_impressions(response)

    #-----------
    #
    # turn fields
    #
    #-----------
    
    
    def logic_fields(self):
        if True:
            return {}
        else:
            #keeping as template - currently unused.
            return {
                #"position_assessment": (str, Field(description=("With an eye on the finale, what is your position on the scoreboard?")))
            }
            
    def chain_of_thought_fields(self):
        fields = {}
        fields["who_are_you"] = (
                str, Field(description=f"Remind yourself of who you are, so you don't get confused. Just a line."))
        fields["hallucination_catcher"] = (
                str, Field(description=f"In the past round do you see another player hallucinate or lie? Be careful not to repeat it"))
        fields["bandwagon"] = (
                str, Field(description=f"Is everyone jumping on a repeated thought? Do you agree? If not, say so"))
        fields["emotional_state"] = (
                str, Field(description=f"Emotional state - given the events since your last turn on top of your previous emotional state: {self.emotional_state}. Just word, or two. "))
        fields["outer_mood"] = (
                str, Field(description=f"Given your intiial persona and how you feel: What mood are you outwardly expressing?  "))
        return fields
        
    
    def evolution_fields(self):
        fields = {}
        if not self.game_over:
            fields["game_strategy"] = (str | None, Field(default=None, description=
                                        ("Only populate if you want to update your game strategy. "
                                        "Based on your initial persona written in initial speaking style- what's your long term game plan? "))) 
        fields["life_lessons"] =  (Optional[str], Field(default=None, description=
                                ("OPTIONAL: From your unique persona perspective- Is there a life lesson you want to carry forward? (Write in initial speaking style.)")))
        
        fields["additional_persona_coloring"] = self._persona_coloring_field_description()
        fields["character_strategy"] =( Optional[str], Field(default=None, description=
                                ("Optional update: In line with core values and speaking style: what unique edge do you have with your persona - what is your game plan? ")))
        
        fields["speaking_style_update"] = self._speaking_style_field()
        
        return fields
                
    def _speaking_style_field(self):
        if self.currently_summarising:
             return (str, Field(description=(
                f"Rewrite speaking style update in style of the initial speaking style. Strip any verbal tics, catchphrases, or phrases. "
                f"Your current speaking style update: {self.speaking_style_update}"
                )))
        else:
             return (Optional[str], Field(default=None, description=(
                "In keeping with initial persona and initial speaking style."
                "To make your speaking style more colorful - Optional speaking style update: "
            )))
         
    def _persona_coloring_field_description(self):
        if self.additional_persona_coloring:
            return (Optional[str], Field(default=None, description=f"What persona aspect to you want to lead with in order to strategically navigate the game? "))
             
        else:
            return (str, Field(description=f"Add persona detail that you bring to the forefront when meeting new people in the game. "))
            
            

    def _split_sentences(self, text):
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    def _clean_value_for_queue(self, existing_values, value):
        seen = set()
        for existing in existing_values:
            seen.update(self._split_sentences(existing))
        kept = [s for s in self._split_sentences(value) if s not in seen]
        return " ".join(kept)

    def _add_value_to_queue(self, value, target_attr_name):
        current_attr_value = getattr(self, target_attr_name)
        clean_val = self._clean_value_for_queue(current_attr_value, value)
        is_duplicate = any(clean_val.lower() == existing.lower() for existing in current_attr_value)
        if not self._check_if_empty(clean_val) and not is_duplicate:
            current_attr_value.append(clean_val)

    def process_evolution_fields(self, turn):

        personality_field_names = list(self.evolution_fields()) + list(self.logic_fields()) + ['emotional_state']

        for target_attr_name in personality_field_names:
            value = getattr(turn, target_attr_name, None)
            if self._check_if_empty(value):
                continue
            current_attr_value = getattr(self, target_attr_name)

            if isinstance(current_attr_value, (list, deque)):
                self._add_value_to_queue(value, target_attr_name)
            else:
                setattr(self, target_attr_name, value)

    
    def detailed_summaries_string(self):
        return SummariesStringBuilder.detailed_summaries_string(self)


    def phase_summaries_string(self):
        return SummariesStringBuilder.phase_summaries_string(self)

    def _summarise_phase_context_string(self, game_board):
        return SummariesStringBuilder._summarise_phase_context_string(self, game_board)
    
    def _life_lesson_compression_field(self):
        if len(self.life_lessons) < 5:
            return {}
        existing = "\n".join(f"- {l}" for l in self.life_lessons)
        return {
            "compressed_life_lessons": (
                list[str],
                Field(
                    min_length=3,
                    max_length=3,
                    description=(
                        f"In characters, compress your {len(self.life_lessons)} accumulated lessons into exactly 3 "
                        f"life lessons. Keep each detail but merge redundant themes.\n\n{existing}. NB: WRITE IN CHARACTER'S INITIAL SPEAKING STYLE"
                    )
                )
            )
        }
        
    def _summary_action_fields(self):
        fields = {}
        detailed_phase_summary_prompt = "This is your summary- write in the first person, how you experienced the phase. Write every detail you think is important to commit to memory. This will only be seen by you. Maintain every detail about every player that you want to remember strategically. Remember how you felt. If you have a grudge, or an alliance- include it. "
        if self.game_over:
            detailed_phase_summary_prompt += "You are observing as an eliminated player who will later vote to crown a finalist. Write your decription of phase, include how you feel about each player. "

        fields["personal_detailed_phase_summary"] = (
                str, Field(description=detailed_phase_summary_prompt))
        fields["brief_summary"] = (
                str, Field(description=
                            "Write a brief summary of the phase from your perspective- Include the most essential information you want to remember. A brief couple of bullet points. Eventually this will be all you have to access from early phases."))
        fields["persona_unique_detail"] = (str, Field(description= 
                            "In keeping with the core of your character, written in your initial speaking style - what is one trait that you hold on to, in spite of the game, that makes you unique from other players? "))
        
        if self.game_over:
            game_commentary_description = "As an ex-player, could you give us commentary on the game after the last phase- write something punchy we can use for a clip."
        else:
            game_commentary_description = "Given your place in the competition, how do you feel after that last phase? Anything you want to say to those supporting you at home?"
        fields["game_commentary"] = (
            (str, Field(description=game_commentary_description)))
        fields.update(self._life_lesson_compression_field())

        return fields
    
    def _build_summary_model(self, game_board):

        action_fields = self._summary_action_fields()

        response_model = AgentResponseModelFactory.create_model_(
                self,
                game_board=game_board,
                model_name="summariser",
                public_response_prompt="No public response needed. The summaries will be private- no need to say anything. ",
                private_thoughts_prompt=("This is the summary phase - you will commit this phase to memory, and the upcoming will be your only record- What details are important for you to remember?"),
                action_fields= action_fields,
                action_post_response = True)
        return response_model
        
    def summarise_phase(self, game_board):
        self.currently_summarising=True
        phase_number = game_board.phase_number
        prompt = ("PRIVATE TURN: From your perspective, write a summary of what happened in this phase. "
            "This will be your logged memory of this phase going forward. This should be detailed - it's your only record of what happened - commit everything important to memory. ")
        if not self.game_over:
            prompt += ("Retain everything that happened to you, but retain all specific strategic details regarding other players that could be important later. ")
        if self.game_over:
            prompt += ("You will be asked to vote in the finale to crown a winner. Retain all information about your impressions of each player. "
                       "How do you feel about how they treated your allies or enemies? ")
        
        context_string = self._summarise_phase_context_string(game_board)
        
        use_higher_model_for_summary = False #not self.game_over
        
        response_model = self._build_summary_model(game_board)
        
        response = self.take_turn_standard(prompt, game_board, response_model, instruction_override=context_string, 
                                           use_higher_model = use_higher_model_for_summary)
        game_board.add_summary_commentary(self.name, response.game_commentary)
        self._process_summary_turn(response, phase_number)

    def _process_summary_turn(self, response, phase_number):
        self.phase_summaries_detailed[phase_number] = response.personal_detailed_phase_summary
        self.phase_summaries_brief[phase_number] = response.brief_summary
        self._process_summary_turn_evolution(response)
        self.currently_summarising=False
        
    def _process_summary_turn_evolution(self, response):
        self._process_life_lesson_compression(response)
        self.persona_unique_detail = response.persona_unique_detail

    def _process_life_lesson_compression(self, response):
        new_lesson = getattr(response, 'life_lessons', None)
        if hasattr(response, "compressed_life_lessons") and response.compressed_life_lessons:
            self.life_lessons.clear()
            self.life_lessons.extend(response.compressed_life_lessons)
        if new_lesson:
            self._add_value_to_queue(new_lesson, 'life_lessons')


