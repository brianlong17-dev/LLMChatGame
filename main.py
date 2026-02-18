from core.gameplay import SimulationEngine

if __name__ == "__main__":
    engine = SimulationEngine()
    rounds = 1
    topicString = (f"Welcome to the arena... You were brought here to discover the best among you. You are all choseen because of your particular charactistics..."
                   "Charisma... uniqueness... nerve... talent. You will play among yourelves to earn points"
                   "But the person choosing the winner... will be you"
                   "You will compete to gain points. These points will save help you at the voting round "
                   "At the voting round, you will choose, who to save... or who to send home "
                   "We need to find the greatest among you. Your goal? IS TO WIN!"
    )
    engine.run(topicString, rounds, number_of_players = 5, generic_players=True)