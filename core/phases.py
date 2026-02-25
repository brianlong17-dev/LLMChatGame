
from typing import Optional

from pydantic import BaseModel

from core.gameplay_definitions_config import *


class PhaseRecipe(BaseModel):
    pre_game_discussion_rounds: int = 2
    mini_game: Optional[GameDefinition] = None
    pre_vote_discussion_rounds: int = 1
    vote_type: Optional[VoteDefinition] = None
    post_vote_discussion_rounds: int = 0
    immunity_types: Optional[List[ImmunityDefinition]] = None  # e.g., ["winner_immunity", "public_vote_immunity"]
    
    def phase_intro_string(self, phase_number, num_players):
        phase_description = f"🚨 WELCOME PLAYERS, TO PHASE {phase_number} 🚨\n"
        #TODO this is temp
        if num_players == 2:
            phase_description = f"🚨 Only two players remain. Unfortunately only one player can win. Only one player will remain at the end of this phase. The player with the most points. Act accordingly. Accept your fate, or fight 🚨\n"
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
            round_summary += f"{self.mini_game.display_name} - {self.mini_game.rules_description}\n"
        for _ in range(self.pre_vote_discussion_rounds):
            round_summary += f'Discussion round\n'
        if self.vote_type:
            round_summary += f"{self.vote_type.display_name} - {self.vote_type.rules_description}\n"
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
    def quick_phase(cls, game, vote, immunity=None):
        return cls.make_phase(0, game, 0, vote, 0, immunity)
    
    @classmethod
    def chatty_phase(cls, game, vote, immunity=None):
        return cls.make_phase(1, game, 1, vote, 1, immunity)
    
    @classmethod
    def mid_phase(cls, game, vote, immunity=None):
        return cls.make_phase(1, game, 0, vote, 0, immunity)     
            
    @classmethod
    def get_phase_recipe(cls, phase_number, agent_number):
        # 1. Finale Override
        if phase_number == -1:
            #intro
            return cls.make_phase(0, PRISONERS_DILEMMA , 0, None, 0, [WILDCARD_IMMUNITY])
        if phase_number == -2:
            #intro
            return cls.make_phase(0, SACRIFICER, 0, None, 0, [])
        if phase_number == -1:
            #intro
            return cls.make_phase(0, PRISONERS_DILEMMA, 0, EACH_PLAYER_VOTES_TO_REMOVE_BEST_NOT_MISS, 1, [HIGHEST_POINT_IMMUNITY_ONLY_ONE])
        
        
        if agent_number <= 2:
            return cls.make_phase(2, PRISONERS_DILEMMA, 0, LOWEST_POINTS_REMOVED, 1, [])

        # 2. Define the variables to test
        games = [
            GIVER,
            STEALER,
            SACRIFICER,
            PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER,
            PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_WINNER, 
            PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER
        ]
        immunities = [WILDCARD_IMMUNITY, HIGHEST_POINT_IMMUNITY, HIGHEST_POINT_IMMUNITY_ONLY_ONE]
        
        votes = [
            EACH_PLAYER_VOTES_TO_REMOVE, 
            EACH_PLAYER_VOTES_TO_REMOVE_BEST_NOT_MISS, 
            LOWEST_POINTS_REMOVED, 
            WINNER_CHOOSES
        ]

        # 3. Build the schedule sequence dynamically
        # Creates a list of tuples: (Game, Vote)
        schedule = [(g, None, None) for g in games] #+ \
                   # [(None, v, None) for v in votes] 
                    
        schedule += [(None, EACH_PLAYER_VOTES_TO_REMOVE, [i]) for i in immunities]

        # 4. Serve the recipe based on the current phase
        idx = phase_number - 1
        if idx < len(schedule):
            game, vote, immunity = schedule[idx]
            return cls.mid_phase(game, vote, immunity)
            
        # 5. Fallback loop (when testing is done but >2 players remain)
        return cls.make_phase(0, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 0, EACH_PLAYER_VOTES_TO_REMOVE, 0, [HIGHEST_POINT_IMMUNITY_ONLY_ONE])
    
    @classmethod
    def get_phase_recipe2(cls, phase_number, agent_number):
        # 1. Define the Menu of Recipes
        intro = cls.chatty_phase(PRISONERS_DILEMMA, EACH_PLAYER_VOTES_TO_REMOVE_BEST_NOT_MISS, [HIGHEST_POINT_IMMUNITY])
        #intro = cls.make_phase(1, None, 0, EACH_PLAYER_VOTES_TO_REMOVE_BEST_NOT_MISS, 0, [HIGHEST_POINT_IMMUNITY])
        
        points_builder_1 = cls.quick_phase(PRISONERS_DILEMMA, EACH_PLAYER_VOTES_TO_REMOVE_BEST_NOT_MISS, [HIGHEST_POINT_IMMUNITY])
        points_builder_2 = cls.make_phase(1, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 1, EACH_PLAYER_VOTES_TO_REMOVE, 0, [])
        
        regular_1 = cls.chatty_phase(PRISONERS_DILEMMA, EACH_PLAYER_VOTES_TO_REMOVE, [])
        
        regular_2 = cls.make_phase(0, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 0, EACH_PLAYER_VOTES_TO_REMOVE, 0, [])
        regular_3 = cls.make_phase(0, PRISONERS_DILEMMA_CHOOSE_PARTNER_ORDER_LOSER, 0, EACH_PLAYER_VOTES_TO_REMOVE, 0, [HIGHEST_POINT_IMMUNITY_ONLY_ONE])
        final = cls.make_phase(2, PRISONERS_DILEMMA, 0, LOWEST_POINTS_REMOVED, 1, [])

        # 2. Handle the Game-Ending Override First
        if agent_number == 2:
            return final
        if phase_number >= 7 or phase_number <=0: #zero wont happen
            return regular_2


        # 3. The Schedule (Dictionary Mapping)
        # Easily map which phase gets which recipe. 
        phase_schedule = {
            1: intro,
            2: points_builder_1,
            3: regular_1,
            # 4: regular_1,
            # 5: regular_1, # Assigning the same recipe to multiple phases is clean and explicit
            # 6: regular_2,
            # 7: regular_2
        }
        
        return phase_schedule.get(phase_number, cls.get_phase_recipe((phase_number - 1), agent_number))
        