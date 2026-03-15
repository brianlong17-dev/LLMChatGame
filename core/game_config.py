class GameConfig:
    """
    Plain config holder for all mini-game values.
    Keep this as data only; behavior and strings stay in game classes.
    """

    def __init__(self):
        
        self.testing_human_as_agent = False
        
        self.discussion_round_topic = "Chat and strategise"
        
        self.inject_host_question = True
        
        self.execution_style = False
        # --------------------------------------------------------------
        # Global / scoreboard defaults
        # --------------------------------------------------------------
        self.starting_score = 0
        self.minimum_score_floor = 0
        self.points_per_survived_vote = 2
        

        # --------------------------------------------------------------
        # Guess The Number
        # --------------------------------------------------------------

        self.guess_number_range = 2  # convenience alias (legacy style)

        # --------------------------------------------------------------
        # Prisoner's Dilemma
        # --------------------------------------------------------------
        self.pd_points_split = 3
        self.pd_points_steal = 5
        self.pd_points_both_steal = 1
        self.pd_odd_player_auto_points = 3
        
        self.pd_pairing_choice_none = 'none'
        self.pd_pairing_choice_random = 'random'
        self.pd_pairing_choice_lowest = 'lowest'
        self.pd_pairing_method = self.pd_pairing_choice_none

        # --------------------------------------------------------------
        # Targeted Choice games (Give / Steal / Sacrifice)
        # --------------------------------------------------------------
        self.targeted_points_award = 3     # Give game
        self.targeted_points_steal = 3     # Steal game max transfer
        self.targeted_points_sacrifice_ratio = 1  # 1 self-point spent = 1 damage
        self.targeted_allow_pass = True
        self.targeted_pass_label = "Pass"

        # --------------------------------------------------------------
        # Sob Story performance game
        # --------------------------------------------------------------
        
        self.sob_story_score_min = 1
        self.sob_story_score_max = 10
        self.sob_story_invalid_score_fallback = 5
        self.sob_story_use_higher_model_for_generation = True
        
        # --------------------------------------------------------------
        # Votes
        # --------------------------------------------------------------
        self.vote_bottom_two_multiple = False
        self.vote_dont_miss = True
        self.vote_missed_points = 2

        # --------------------------------------------------------------
        # Immunities
        # --------------------------------------------------------------
        self.immunity_highest_points_only_one = False
        
        # --------------------------------------------------------------
        # Quick per-game identity helpers (optional)
        # --------------------------------------------------------------
        self.game_names = {
            "guess": "Guess the number",
            "pd": "Prisoner's Dilemma",
            "give": "Giver",
            "steal": "Stealer",
            "sacrifice": "Sacrificer",
            "sob_story": "Perform your sob story",
        }

    def set_guess_range(self, number):
        self.guess_number_range = number
    
    def set_pd_pairing_none(self):
        self.pd_pairing_method = self.pd_pairing_choice_none
    
    def set_pd_pairing_random(self):
        self.pd_pairing_method = self.pd_pairing_choice_random
    
    def set_pd_pairing_lowest(self):
        self.pd_pairing_method = self.pd_pairing_choice_lowest
    