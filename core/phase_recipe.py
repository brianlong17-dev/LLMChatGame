
from typing import List, Optional, Type

from pydantic import BaseModel, ConfigDict

from core.game_config import GameConfig

from gameplay_management.discussion_round import DiscussionRound
from gameplay_management.unified_controller import *

class PhaseRecipe(BaseModel):
    rounds: List[Type[BaseRound]] = None 
    immunity_types: Optional[List[Type[ImmunityMechanicsMixin]]] = None  # e.g., ["winner_immunity", "public_vote_immunity"]
    overall_game_rules: Optional[str] = None #if not none will be sent to the phase runner for the context builder
    
    def phase_summary_string(self, game_manager):
        round_summary = '\n-----------------\n'
        for round in self.rounds:
            round_summary += f"{round.display_name(game_manager)} - {round.rules_description(game_manager)}\n"
        round_summary += '-----------------\n'
        return round_summary
    
    def phase_progress_string(self, game_manager, current_index):
        round_summary = '\n-----------------\n'
        current_index -= 1 
        for i, round in enumerate(self.rounds):
            if i < current_index:
                status = "COMPLETED"
            elif i == current_index:
                status = "CURRENTLY ONGOING"
            else:
                status = "UPCOMING"
            
            round_summary += f"{round.display_name(game_manager)} - {status}\n"
        round_summary += '-----------------\n'
        round_summary += self.detailed_rules_string(game_manager, current_index)
       
        return round_summary 
    
    def detailed_rules_string(self, game_manager, current_index):
        rules_string = '\n-----------------\n'
        rules_string += '------- UPCOMING GAME RULES ----------\n'
        for i, round in enumerate(self.rounds):
            if i > current_index:
                if round.is_game() or round.is_vote():
                    rules_string += f"{round.display_name(game_manager)} - {round.rules_description(game_manager)}\n"
        rules_string += '-----------------\n'
        return rules_string
        
        
    def phase_intro_string(self, phase_number, num_players, game_manager): #game_manager
        #this should not be here
        phase_description = f"🚨 WELCOME PLAYERS, TO PHASE {phase_number} 🚨. "
        
        #TODO this is temp
        
        if num_players == 2:
            phase_description = f"🚨 Only two players remain. Unfortunately only one player can win. Only one player will remain at the end of this phase. The player with the most points. Act accordingly. Accept your fate, or fight 🚨\n"
        
        #--------------------
        
        phase_description += f"In this round we will have: "
        
        discussion_rounds = [round for round in self.rounds if round.is_discussion()]
        if len(discussion_rounds) == 1:
            phase_description += "A discussion round. "
        elif len(discussion_rounds) > 1:
            phase_description += "Discussion rounds. "
            
            
        if any(round.is_game() for round in self.rounds):
            phase_description += "A Game Round. "
            
        has_elimination = any(round.is_vote() for round in self.rounds)
        if has_elimination:
            phase_description += "An Elimination. "
        
        
        if has_elimination and self.immunity_types:
            immunity_message = f"HOWEVER! This elimination round has the following immunities in play:\n"
            for immunity in self.immunity_types:
                immunity_message += f"- {immunity.display_name(game_manager)}: {immunity.rules_description(game_manager)}\n"
            phase_description += immunity_message
        
      
        return phase_description
        
    

class PhaseRecipeFactory:
    
    @classmethod
    def make_phase(self, pre_game_discussion_rounds, game, pre_vote_discussion_rounds, 
                   vote, post_vote_discussion_rounds, immunity_types):
        rounds = []
        
        for _ in range(pre_game_discussion_rounds):
            rounds.append(DiscussionRound)
        if game:
            rounds.append(game)
        
        for _ in range(pre_vote_discussion_rounds):
            rounds.append(DiscussionRound)
        if vote:
            rounds.append(vote)
        for _ in range(post_vote_discussion_rounds):
            rounds.append(DiscussionRound)
            
        return PhaseRecipe(rounds=rounds, immunity_types=immunity_types)
        
    
    
    @classmethod
    def quick_phase(cls, game, vote, immunity=None):
        return cls.make_phase(0, game, 0, vote, 0, immunity)
    
    @classmethod
    def chatty_phase(cls, game, vote, immunity=None):
        return cls.make_phase(1, game, 1, vote, 1, immunity)
    
    @classmethod
    def mid_phase(cls, game, vote, immunity=None):
        vote_discussion = 1 if vote else 0
        return cls.make_phase(1, game, vote_discussion, vote, 0, immunity)     
    
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
    def get_phase_recipe(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
        return cls.get_phase_compelling(phase_number, agent_number, cfg, voting, incl_games, speed)
    
    @classmethod
    def get_phase_compelling(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
        
        cfg.vote_bottom_two_multiple = True
        if agent_number == 2:
            return cls.mid_phase(GamePrisonersDilemma, VoteLowestPoints, [])
        
        index_rounds = []
        if phase_number == 1:
            cfg.set_guess_range(2)
            return cls.make_phase(1, GameGuess, 0, None, 0, None)  
        if phase_number == 2:
            cfg.set_guess_range(3)
            return cls.make_phase(1, GameGuess, 1, VoteEachPlayer, 0, [HighestPointsImmunity, WildcardImmunity]) 
            return cls.mid_phase(GameGuess, None, [])
        if phase_number == 3:
            return cls.mid_phase(GameTargetedChoiceGive, VoteEachPlayer, [HighestPointsImmunity, WildcardImmunity])
        if phase_number == 4:
            return cls.mid_phase(GameTargetedChoiceSteal, VoteBottomTwo, [])
        if phase_number == 5:
            return cls.mid_phase(GamePerformSobStory, VoteBottomTwo, [])
        if phase_number == 6:
            cfg.set_pd_pairing_lowest()
            return cls.mid_phase(GamePrisonersDilemma, VoteBottomTwo, [])
        
        return cls.mid_phase(GamePrisonersDilemma, VoteBottomTwo, [])
        
    
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
    
        simple_games = [GameGuess,
            GamePrisonersDilemma,
            GameTargetedChoiceGive,
            GameTargetedChoiceSteal,
            GamePerformSobStory]
        
        sg_len = len(simple_games)
        if phase_number <= sg_len:
            game =  simple_games[phase_number - 1]
            return cls.mid_phase(game, None, [])
        
        if phase_number == sg_len + 1:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_none
            return cls.quick_phase(GamePrisonersDilemma, None, [])
        if phase_number == sg_len + 2:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_random
            return cls.quick_phase(GamePrisonersDilemma, None, [])
        elif phase_number == sg_len + 3:
            cfg.pd_pairing_method = cfg.pd_pairing_choice_lowest
            return cls.quick_phase(GamePrisonersDilemma, None, [])
        
        
    
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
            return cls.quick_phase(GameGuess, VoteEachPlayer, [VoteEachPlayer])
        
        if phase_number == 4:
            cfg.vote_dont_miss = False
            return cls.quick_phase(GameGuess, VoteEachPlayer, [])
    
    @classmethod
    def get_phase_recipe_test_master(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
       
        # 1. Define the test games
        test_games = [
            GameGuess,                   # Phase 1
            GamePrisonersDilemma,         # Phase 2
            GameTargetedChoiceGive,      # Phase 3
            GameTargetedChoiceSteal,     # Phase 4
            GameTargetedChoiceSacrifice, # Phase 5
            GamePerformSobStory    # Phase 6
        ]
        
        # 2. Define Eliminations as tuples: (Voting_Method, [Immunities])
        # Using None for rounds where we just want to play the game and build context
        test_eliminations = [
            (None, []),                                      # Phase 1: Safe round
            (VoteBottomTwo , [HighestPointsImmunity]),       # Phase 2: Elimination 1
            (None, []),                                      # Phase 3: Safe round
            (VoteLowestPoints, [HighestPointsImmunity]),     # Phase 4: Elimination 2
            (None, []),                                      # Phase 5: Safe round
            (VoteEachPlayer, [WildcardImmunity])              # Phase 6: Elimination 3
        ]

        idx = phase_number - 1

        # 3. Check if we've exhausted all test lists. If so, trigger the default endgame.
        if idx >= len(test_games) and idx >= len(test_eliminations):
            current_game = GamePrisonersDilemma
            current_voting = VoteBottomTwo
            current_immunities = []
        else:
            # 4. Safely pull from lists, defaulting to None/empty if the index exceeds that specific list
            current_game = test_games[idx] if idx < len(test_games) else None
            
            if idx < len(test_eliminations):
                current_voting, current_immunities = test_eliminations[idx]
            else:
                current_voting, current_immunities = None, []

        # 5. Apply any necessary config tweaks based on the current setup
        if current_voting == VoteBottomTwo:
             cfg.vote_bottom_two_multiple = False
        if current_game == GamePrisonersDilemma:
             cfg.pd_pairing_method = cfg.pd_pairing_choice_lowest

        # 6. Return the assembled phase based on the requested speed
        if speed == 3:
            return cls.chatty_phase(current_game, current_voting, current_immunities)
        elif speed == 2:
            return cls.mid_phase(current_game, current_voting, current_immunities)
        else:
            return cls.quick_phase(current_game, current_voting, current_immunities)
      
        
        
     
