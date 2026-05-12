from core.levels.phase_recipe_factory import *


class PhaseRecipeFactoryBeginner(PhaseRecipeFactory):
    #TODO review all of this again
    
    "I think we should have have a phase 0"
    
    
    def intro():
        pass
        "Hey so, here we are the game ... "
        "This is a simple game - you will play against X players ."
    def phase_intro(rounds):
        pass
    
    
    @classmethod
    def get_game_rules(cls):
        #depreciated, but this is something that will go into intro
        return "In this game, you will play rounds of prisoner's dilemma. After each game, the bottom two players face the vote to be eliminated. "
        
    @classmethod
    def get_phase_recipe(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games = True, speed=1):
        return cls.get_phase(phase_number, agent_number, cfg, voting, incl_games, speed)
   

    @classmethod
    def get_phase(cls, phase_number, agent_number, cfg: GameConfig, voting=None, incl_games=True, speed=1):
        cfg.vote_bottom_two_multiple = True
        
        if agent_number == 4:
            rounds = [GamePrisonersDilemma, DiscussionRound, VoteBottomTwo]
            config_mutations=[("set_pd_pairing_random", [])]
            return PhaseRecipe(rounds=rounds, config_mutations=config_mutations)
        
            
        if agent_number == 3:
            rounds = [GamePrisonersDilemma, DiscussionRound, VoteBottomTwo]
            config_mutations=[("set_pd_pairing_all", [])]
            return PhaseRecipe(rounds=rounds, config_mutations=config_mutations)
        
        
        if agent_number == 2:
            rounds = [GamePrisonersDilemma, VoteLowestPoints]
            config_mutations=[("set_pd_pairing_all", [])]
            return PhaseRecipe(rounds=rounds, config_mutations=config_mutations)
        

