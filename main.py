from core.gameplay import SimulationEngine

if __name__ == "__main__":
    engine = SimulationEngine()
    rounds = 1
    topicString = (f"At the end of {rounds} rounds, each player votes off another player. "
                   "The player with the most votes against them will be ELIMINATED. THE GOAL IS THE BE THE LAST PLAYER STANDING!"
    )#f"In the final round, the player with the most points from the judge wins")
    engine.run(topicString, rounds, number_of_players = 3, generic_players=True)