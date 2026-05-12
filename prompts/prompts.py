class PromptLibrary:
    #Agent
    line_break = (f"\n{"="*50}")
    desc_persona_update = ("Only populate this field with a genuine evolution in your persona - "
        "You should include details from your existing persona that stil apply. "
        "Only include broad general traits that last beyond the current round. "
        "Include any character traits, style or backstory that defines you. "
    )
    desc_agent_updated_game_strategy = ("Only populate if you want to update your game strategy. "
                                          "Based on how the game works, what is the smartest strategy?")
    desc_action_agent = ("A visible physical action. Players may not speak in the future tense about their plans. You must describe the action you are taking right now in the present tense.")
    desc_message = "Your spoken words. What will you say? Stay in character. What you say is revealed to the group"
    desc_agent_lifeLessons = ("A new lesson to you mind that you will take forward. This will shape your future descisions. Take key lessons only, so you don't cloud your decision making.")
    desc_agent_mathematical_assessment = ("What's your assessment of the scoreboard and your place in it?")
    desc_agent_speaking_style = (
        "Only populate this field if your speaking style has genuinely evolved or shifted during this round — "
        "for example, update in response to a change in mood or strategy. "
        "If nothing has changed, leave this blank. Do NOT explain or comment on why no change is needed."
        "If possible, the speaking style should be approximately as long and detailed as the previous speaking style."
        "If you have had a vocal tic for many turns, consider replacing it."
    )
    desc_basic_thought = "Your internal thoughts. Strategy, feelings, and private observations."
    desc_basic_public_response = "What you actually say out loud to the group. Stay in character!"
   
    #Gameplay
    desc_agent_names = "The name of the agent (e.g. 'Agent Alpha')"

    @staticmethod
    def final_words_prompt():
        return (
            f"---------------------------------------------------------------------\n"
            f"🛑 GAME OVER 🛑\n"
            f"You have just been ELIMINATED. Your game is finished.\n"
            f"Do not plan for the next round. Do not try to save yourself.\n"
            f"Your Goal: Give a memorable final statement. You can be gracious, angry, confused, or vengeful.\n"
            f"---------------------------------------------------------------------\n"
            f"Your Final Words:"
        )
        
   