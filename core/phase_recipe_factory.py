from core.game_config import GameConfig
from core.phase_recipe import PhaseRecipe
from gameplay_management.discussion_round import DiscussionRound
from gameplay_management.unified_controller import *
from gameplay_management.wake_up_round import WakeUpRound

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
        #TODO refactor all of this 
        index_rounds = []
        if phase_number == 1:
            cfg.set_guess_range(2)
            return cls.make_phase(0, WakeUpRound, 0, VoteEachPlayer, 0, None)  
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
        
    
 