
from typing import Optional

from pydantic import BaseModel

from core.game_configs import *


class PhaseRecipe(BaseModel):
    pre_game_discussion_rounds: int = 2
    mini_game: Optional[GameDefinition] = None
    pre_vote_discussion_rounds: int = 1
    vote_type: Optional[VoteDefinition] = None
    post_vote_discussion_rounds: int = 0
    immunity_types: Optional[List[ImmunityDefinition]] = None  # e.g., ["winner_immunity", "public_vote_immunity"]
    
    def messageString(self, phase_number):
        phase_description = f"🚨 WELCOME PLAYERS, TO PHASE {phase_number} 🚨\n"
        #phase_description += f"Discussion rounds have magic words- figure out what they are and use them to earn points\n"
        phase_description += f"In this round we will have: \n"
        
        game_description = ""
        vote_description = ""
        pre_game_discussion_message = ""
        pre_vote_discussion_message = ""
        immunity_message = ""
        
        dr_count = self.pre_game_discussion_rounds + self.pre_game_discussion_rounds + self.post_vote_discussion_rounds
        
        if dr_count == 1:
            phase_description += "A Discussion Round\n"
        elif dr_count > 1:
            phase_description += "Discussion Rounds\n"
        if self.mini_game:
            phase_description += "A Game Round\n"
        if self.vote_type:
            phase_description += f"An Elimination\n"
        if self.vote_type and self.immunity_types:
            immunity_message += f"HOWEVER! This elimination round has the following immunities in play:\n"
            for immunity in self.immunity_types:
                immunity_message += f"- {immunity.display_name}: {immunity.rules_description}\n"
            phase_description += immunity_message
        
        round_summary = '\n-----------------\n'
        for _ in range(self.pre_game_discussion_rounds):
            round_summary += f'Discussion round\n'
        if self.mini_game:
            round_summary += f"{self.mini_game.display_name}\n"
        for _ in range(self.pre_vote_discussion_rounds):
            round_summary += f'Discussion round\n'
        if self.vote_type:
            round_summary += f"{self.vote_type.display_name}\n"
        for _ in range(self.post_vote_discussion_rounds):
            round_summary += f'Discussion round\n'
        round_summary += '-----------------\n'
        
        return phase_description, round_summary
        
    

class PhaseRecipeFactory(BaseModel):
    
    @classmethod
    def make_phase(self, pre_game_discussion_rounds, game, pre_vote_discussion_rounds, 
                   vote, post_vote_discussion_rounds, immunity_types):
        return PhaseRecipe(
            pre_game_discussion_rounds=pre_game_discussion_rounds,
            mini_game=game,
            pre_vote_discussion_rounds=pre_vote_discussion_rounds,
            vote_type=vote,
            post_vote_discussion_rounds=post_vote_discussion_rounds,
            immunity_types=immunity_types #"HighestPointPlayerImmunity(), WildcardImmunity()]
        )
    @classmethod
    def get_phase_recipe(cls, phase_number, agent_number):
        # --- PHASE DEFINITIONS (The Menu) ---
        
        # Intro: Players get to know each other, random pairings
        intro = cls.make_phase(1, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_RANDOM, 1, WINNER_CHOOSES, 1, [])
        
        # Points Builder 1: Winner picks partner, focus on scoring
        points_builder_1 = cls.make_phase(0, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 1, WINNER_CHOOSES, 0, [])
        
        # Points Builder 2: Loser picks partner, NO elimination (Safe Round)
        points_builder_2 = cls.make_phase(1, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 1, EACH_PLAYER_VOTES_TO_REMOVE, 0, [])
        
        # Regular 1: Standard gameplay with Highest Score Immunity
        regular_1 = cls.make_phase(1, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 1, EACH_PLAYER_VOTES_TO_REMOVE, 0, [])
        
        # Regular 2: High stakes, players vote each other out manually
        regular_2 = cls.make_phase(0, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 0, EACH_PLAYER_VOTES_TO_REMOVE, 0, [])
        
        # Regular 2: High stakes, players vote each other out manually
        regular_3 = cls.make_phase(0, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 0, EACH_PLAYER_VOTES_TO_REMOVE, 0, [HIGHEST_POINT_IMMUNITY_ONLY_ONE])
        
        # Final: The 2-player showdown logic
        final = cls.make_phase(2, PRISONERS_DILEMMA, 0, LOWEST_POINTS_REMOVED, 1, [])

        # --- SELECTION LOGIC ---
        
        if agent_number == 2:
            return final
        
            
        if phase_number == 1:
            return intro
        elif phase_number == 2:
            return regular_1
        elif phase_number == 2:
            return regular_2
        else:
            return regular_3
        
        # elif phase_number == 4:
        #     return regular_1
        # else:
        #     # All rounds from phase 5 onwards use the manual voting style
        #     return regular_2