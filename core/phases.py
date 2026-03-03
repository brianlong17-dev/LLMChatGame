
from typing import List, Optional, Type

from pydantic import BaseModel, ConfigDict

from core.game_config import GameConfig
from gameplay_management.eliminations.vote_mechanicsMixin import VoteMechanicsMixin
from gameplay_management.eliminations.voting_bottom_two import VoteBottomTwo
from gameplay_management.eliminations.voting_each_player import VoteEachPlayer
from gameplay_management.eliminations.voting_lowest_points import VoteLowestPoints
from gameplay_management.eliminations.voting_winner_chooses import VoteWinnerChooses
from gameplay_management.game_targeted.game_targeted_give import GameTargetedChoiceGive
from gameplay_management.game_targeted.game_targeted_sacrifice import GameTargetedChoiceSacrifice
from gameplay_management.game_targeted.game_targeted_steal import GameTargetedChoiceSteal
from gameplay_management.games.game_guess import GameGuess
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from gameplay_management.games.game_perform import GamePerformSobStory
from gameplay_management.games.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.immunities.highest_points_immunity import HighestPointsImmunity
from gameplay_management.immunities.wildcard_immunity import WildcardImmunity
from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin

class PhaseRecipe(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pre_game_discussion_rounds: int = 2
    mini_game: Optional[Type[GameMechanicsMixin]] = None
    pre_vote_discussion_rounds: int = 1
    vote_type: Optional[Type[VoteMechanicsMixin]] = None
    post_vote_discussion_rounds: int = 0
    immunity_types: Optional[List[Type[ImmunityMechanicsMixin]]] = None  # e.g., ["winner_immunity", "public_vote_immunity"]
    
    def phase_intro_string(self, phase_number, num_players, game_manager): #game_manager
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
                immunity_message += f"- {immunity.display_name(game_manager)}: {immunity.rules_description(game_manager)}\n"
            phase_description += immunity_message
        
        round_summary = '\n-----------------\n'
        for _ in range(self.pre_game_discussion_rounds):
            round_summary += f'Discussion round\n'
        if self.mini_game:
            round_summary += f"{self.mini_game.display_name(game_manager)} - {self.mini_game.rules_description(game_manager)}\n"
        for _ in range(self.pre_vote_discussion_rounds):
            round_summary += f'Discussion round\n'
        if self.vote_type:
            round_summary += f"{self.vote_type.display_name(game_manager)} - {self.vote_type.rules_description(game_manager)}\n"
        for _ in range(self.post_vote_discussion_rounds):
            round_summary += f'Discussion round\n'
        round_summary += '-----------------\n'
        
        return phase_description, round_summary
        
    

class PhaseRecipeFactory:
    
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
    def game_intro(cls):
        topicString = (f"Welcome to the arena... You were brought here to discover the best among you. You are all chosen because of your particular characteristics... "
                   "Charisma... uniqueness... nerve... talent. You will play among yourselves to earn points. "
                   "But the person choosing the winner... will be you. "
                   "You will compete to gain points. These points will save help you at the voting round. "
                   "At the voting round, you will choose, who to save... or who to send home. "
                   "We need to find the greatest among you. Your goal? IS TO WIN!"
        )
        return topicString
    
class PhaseRecipeFactoryDefault(PhaseRecipeFactory):
    
    @classmethod
    def get_game_rules(cls):
        "Players are eliminated until one winner remains."
    
    @classmethod
    def get_phase_recipe_test_votes(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
       
        if phase_number == 1:
            return cls.quick_phase(None, VoteWinnerChooses, [])
        
        if phase_number == 1:
            return cls.quick_phase(None, VoteLowestPoints, [])
        
        if phase_number == 1:
            cfg.vote_dont_miss = True
            return cls.quick_phase(None, VoteEachPlayer, [])
        
        if phase_number == 2:
            cfg.vote_dont_miss = False
            return cls.quick_phase(None, VoteEachPlayer, [])
        
        if phase_number == 3:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_none
            cfg.vote_bottom_two_multiple = False
            cfg.vote_dont_miss = False
            return cls.quick_phase(GameGuess, VoteBottomTwo, [])
        
        if phase_number == 4:
            cfg.vote_bottom_two_multiple = True
            cfg.vote_dont_miss = True
            return cls.quick_phase(GameGuess, VoteBottomTwo, [])
        
        if phase_number == 5:
            return cls.quick_phase(GameGuess, VoteBottomTwo, [])
        
       
        games = [
            GamePrisonersDilemma,
            GameTargetedChoiceGive,
            GameTargetedChoiceSteal,
            GameTargetedChoiceSacrifice,
            GamePerformSobStory
        ]
        idx = phase_number - 1 - 2 #top hard coded phase
        if idx < len(games):
            game = games[idx]
            
        if speed == 3:
            return cls.chatty_phase(game, voting, [])
        if speed == 2:
            return cls.mid_phase(game, voting, [])
        else:
            return cls.quick_phase(game, None, [])
        
    @classmethod
    def get_phase_recipe_test_games(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
        
        
        if phase_number == 1:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_none
            return cls.quick_phase(GamePerformSobStory, None, [])
        
        if phase_number == 2:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_none
            return cls.quick_phase(GamePrisonersDilemma, None, [])
        if phase_number == 3:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_random
            return cls.quick_phase(GamePrisonersDilemma, None, [])
        elif phase_number == 4:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_lowest
            return cls.quick_phase(GamePrisonersDilemma, None, [])
        games = [
            GameGuess,
            GamePrisonersDilemma,
            GameTargetedChoiceGive,
            GameTargetedChoiceSteal,
            GameTargetedChoiceSacrifice,
            GamePerformSobStory
        ]
        idx = phase_number - 1 - 2 #top hard coded phase
        if idx < len(games):
            game = games[idx]
            
        if speed == 3:
            return cls.chatty_phase(game, voting, [])
        if speed == 2:
            return cls.mid_phase(game, voting, [])
        else:
            return cls.quick_phase(game, None, [])
    
    @classmethod
    def get_phase_recipe_test_immunities(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
       
        if phase_number == 1:
            cfg.immunity_highest_points_only_one = False
            return cls.quick_phase(GameGuess, VoteEachPlayer, [HighestPointsImmunity])
        
        if phase_number == 2:
            cfg.immunity_highest_points_only_one = True
            return cls.quick_phase(GameGuess, VoteEachPlayer, [HighestPointsImmunity])
        
        if phase_number == 3:
            cfg.vote_dont_miss = True
            return cls.quick_phase(GameGuess, VoteEachPlayer, [WildcardImmunity])
        
        if phase_number == 4:
            cfg.vote_dont_miss = False
            return cls.quick_phase(GameGuess, VoteEachPlayer, [])
        
      
        
        
     
