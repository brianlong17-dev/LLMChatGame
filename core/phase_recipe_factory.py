from core.game_config import GameConfig
from core.phase_recipe import PhaseRecipe
from gameplay_management.discussion_round import DiscussionRound
from gameplay_management.wake_up_round import WakeUpRound
from gameplay_management.games.game_prisoners_dilemma import GamePrisonersDilemma
from gameplay_management.games.game_guess import GameGuess
from gameplay_management.games.game_perform import GamePerformSobStory
from gameplay_management.game_targeted.game_targeted_give import GameTargetedChoiceGive
from gameplay_management.game_targeted.game_targeted_steal import GameTargetedChoiceSteal
from gameplay_management.game_targeted.game_targeted_sacrifice import GameTargetedChoiceSacrifice
from gameplay_management.eliminations.voting_bottom_two import VoteBottomTwo
from gameplay_management.eliminations.voting_each_player import VoteEachPlayer
from gameplay_management.eliminations.voting_lowest_points import VoteLowestPoints
from gameplay_management.immunities.highest_points_immunity import HighestPointsImmunity
from gameplay_management.immunities.wildcard_immunity import WildcardImmunity

class PhaseRecipeFactory:
    
    @classmethod
    def make_phase(self, pre_game_discussion_rounds, game, pre_vote_discussion_rounds,
                   vote, post_vote_discussion_rounds, immunity_types, config_mutations=None):
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

        return PhaseRecipe(rounds=rounds, immunity_types=immunity_types, config_mutations=config_mutations or [])
        
    
    
    @classmethod
    def quick_phase(cls, game, vote, immunity=None, config_mutations=None):
        return cls.make_phase(0, game, 0, vote, 0, immunity, config_mutations)

    @classmethod
    def chatty_phase(cls, game, vote, immunity=None, config_mutations=None):
        return cls.make_phase(1, game, 1, vote, 1, immunity, config_mutations)

    @classmethod
    def mid_phase(cls, game, vote, immunity=None, config_mutations=None):
        vote_discussion = 1 if vote else 0
        return cls.make_phase(1, game, vote_discussion, vote, 0, immunity, config_mutations)     
    
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
    def _phases(cls):
        return [
            None,  # phase 0 unused
            PhaseRecipe(rounds=[WakeUpRound]),
            cls.make_phase(1, GameGuess, 1, VoteEachPlayer, 0, [HighestPointsImmunity, WildcardImmunity],
                           config_mutations=[("set_guess_range", [3])]),
            cls.mid_phase(GameTargetedChoiceGive, VoteEachPlayer, [HighestPointsImmunity, WildcardImmunity]),
            cls.mid_phase(GameTargetedChoiceSteal, VoteBottomTwo, []),
            cls.mid_phase(GamePerformSobStory, VoteBottomTwo, []),
            cls.mid_phase(GamePrisonersDilemma, VoteBottomTwo, [],
                          config_mutations=[("set_pd_pairing_lowest", [])]),
        ]

    @classmethod
    def get_phase_compelling(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games=True, speed=1):
        cfg.vote_bottom_two_multiple = True

        if agent_number == 2:
            return cls.mid_phase(GamePrisonersDilemma, VoteLowestPoints, [])
        if agent_number == 3:
            return cls.mid_phase(GamePrisonersDilemma, VoteLowestPoints, [],
                                 config_mutations=[("set_pd_pairing_all", [])])

        phases = cls._phases()
        if phase_number < len(phases):
            return phases[phase_number]
        return phases[-1]
        
    
 