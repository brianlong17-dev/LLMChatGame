from textwrap import dedent

class GamePromptLibrary:
    pd_split = 3
    pd_steal = 5
    pd_both_steal = 1
    
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