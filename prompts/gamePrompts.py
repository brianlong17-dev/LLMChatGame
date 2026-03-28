from textwrap import dedent

class GamePromptLibrary:
    points_per_survived_vote = 2

    model_field_error = "error_string"
    
    model_field_choose_name = "target_name"
    invalid_target_message = (
        "{player_name} chose '{target_name}'... but that's an invalid target. No points changed hands."
    )
    #------------------------ votes ----------------------- #
    dont_miss_string = "A player that receives votes but is not eliminated will receive {points} points per failed vote. "
    
    
    #------------------------ sob story ----------------------- #
    sob_story_host_intro = (
            "💔 SOB STORY!\n"
            "Every reality contestant has one — a traumatic past, a hurdle they overcame, "
            "the people left behind. Now is your chance to share your vulnerability.\n"
            "Your fellow contestants will judge your story on a scale of 1-10. "
            "Did it pull at the heartstrings? Was it honest, vulnerable — and do they even like you?"
        )
    
    sob_story_prompt = (
            "Write your sob story. Pour your heart out — or don't. "
            "Make it heartwarming, heartstring-tugging, honest, vulnerable, "
            "absurd, strategic... whatever you think will move your fellow contestants. "
            "Your public response IS your story."
        )
    
    
    #------------------------ Rock Paper Scissors ----------------------- #
    rps_game_intro = (
        "✊📄✂️  ROCK PAPER SCISSORS!\n"
        "It's the oldest game in the book — pure instinct, pure psychology.\n"
        "You'll be paired up and make your move simultaneously. "
        "Read your opponent, trust your gut, and may the best hand win!"
    )

    rps_game_prompt = (
        "✊📄✂️  ROCK PAPER SCISSORS!\n"
        "You are facing {opponent_name}.\n"
        "Points on the line:\n"
        "{points_string}"
        "Choose your move — what will it be?"
    )

    #------------------------ Prisoner's Dilemma ----------------------- #
    pd_game_prompt = (
            f"🚨 PRISONER'S DILEMMA 🚨\n"
            "You have been paired with {opponent_name}.\n"
            f"Remember:\n"
            "{points_rules_string}"
            f"Based on your game history and personality, make your choice."
        )
    
    targeted_games_points = 3
    give_game_intro = (f"Well, enough of the scheming, lying, conning... whatever happened to giving!? "
        f"In this round, you will get to pick a pal. The player you pick will receive {targeted_games_points} points! "
        f"Everyone is happy! Well... except any player with no friends! hehe")
    give_game_player_intro = ("{player_name}! You're up- what player are you choosing, and why?")

    @classmethod
    def prisonersDilemmaIntro(cls, pairing_string: str, points_rules_string: str):
        return (
            f"It's time to play: Prisoner's Dilemma.\n"
            f"{pairing_string}\n"
            f"In each pairing you get a choice: SPLIT or STEAL.\n"
            f"{points_rules_string}\n\n"
        )
