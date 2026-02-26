from textwrap import dedent

class GamePromptLibrary:
    pd_split = 3
    pd_steal = 5
    pd_both_steal = 1
    
    model_field_error = "error_string"
    
    model_field_choose_name = "target_name"
    invalid_target_message = (
        "{player_name} chose '{target_name}'... but that's an invalid target. No points changed hands."
    )
    
    pd_desc_string = f"Stealing from a a splitter: {pd_steal} points and 0 points. Both split: {pd_split} points each, both steal: {pd_both_steal} point each."
    pd_game_prompt = (
            f"🚨 PRISONER'S DILEMMA 🚨\n"
            "You have been paired with {opponent_name}.\n"
            f"Remember:\n"
            f"- If you both SPLIT, you both get {pd_split} points.\n"
            f"- If you STEAL and they SPLIT, you get {pd_steal} points and they get 0.\n"
            f"- If you both STEAL, you both get {pd_both_steal} point.\n"
            f"Based on your game history and personality, make your choice."
        )
    
    targeted_games_points = 3
    give_game_intro = (f"Well, enough of the scheming, lying, conning... whatever happened to giving!? "
        f"In this round, you will get to pick a pal. The player you pick will receive {targeted_games_points} points! "
        f"Everyone is happy! Well... except any player with no friends! hehe")
    give_game_player_intro = ("{player_name}! You're up- what player are you choosing, and why?")

    @classmethod
    def prisonersDilemmaIntro(cls, choose_partner: bool, winner_picks_first = True):
        splitPoints = cls.pd_split
        stealPoints = cls.pd_steal
        bothSteal = cls.pd_both_steal
        pairing_string = ("At random, players will get to choose who to couple up with for the game")
        winner_picks_string = ("")
        if choose_partner:
            pairing_string = "Players will get to choose who to couple up with for the game"
            if winner_picks_first:
                winner_picks_string = "The player with the most points gets to pick their partner first, and so on"
            else:
                winner_picks_string = "To level the playing field, our player with the lowest points will pick their partner first, and so on up the line"
            
            
        
        # 1. Broadcast the rules
        intro_message = (
            f"It's time to play a game to build points. "
            f"It's time to find out who your real friends are. Who to trust, and who to play. "
            f"The game: Prisoner's Dilemma.\n"
            f"{pairing_string}\n"
            f"{winner_picks_string}\n"
            f"In each pairing you get a choice: SPLIT or STEAL.\n"
            f"- If both players decide to SPLIT, they will receive {splitPoints} points each.\n"
            f"- If one player decides to STEAL while the other splits, the stealer receives {stealPoints} points, and the victim gets 0.\n"
            f"- If both choose to STEAL, they will receive {bothSteal} point each. \n\n")
        
        return intro_message
