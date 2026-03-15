class PromptLibrary:
    #Agent
    line_break = (f"\n{"="*50}")
    desc_persona_update = "Your evolving personality. Change and grow."
    desc_agent_updated_strategy_to_win = "UPDATE if you want to UPDATE your strategy to win. Based on how the game works, what is the smartest strategy to win?"
    desc_action_agent = ("A visible physical action. Players may not speak in the future tense about their plans. You must describe the action you are taking right now in the present tense.")
    desc_message = "Your spoken words. What will you say? Stay in character. What you say is revealed to the group"
    desc_agent_lifeLessons = ("A new lesson to you mind that you will take forward. This will shape your future descisions. Take key lessons only, so you don't cloud your decision making.")
    desc_agent_mathematical_assessment = ("What's your assessment of the scoreboard and your place in it?")
    desc_agent_speaking_style = ("UPDATE ONLY WITH EVOLUTION. How the character speaks — vocabulary, tone, cadence. Populate if the character's speaking style is evolving in response to what happened in the game")
    
    desc_basic_thought = "Your internal thoughts. Strategy, feelings, and private observations."
    desc_basic_public_response = "What you actually say out loud to the group. Stay in character!"
   
    #Gameplay
    desc_agent_names = "The name of the agent (e.g. 'Agent Alpha')"

    @staticmethod
    def final_words_prompt(gameBoard):
        history_context = gameBoard.context_builder.get_full_context()
        return (
            f"CONTEXT:\n{history_context}\n\n"
            f"---------------------------------------------------------------------\n"
            f"🛑 GAME OVER 🛑\n"
            f"You have just been ELIMINATED. Your game is finished.\n"
            f"Do not plan for the next round. Do not try to save yourself.\n"
            f"Your Goal: Give a memorable final statement. You can be gracious, angry, confused, or vengeful.\n"
            f"---------------------------------------------------------------------\n"
            f"Your Final Words:"
        )
        
    # System Prompts
    @staticmethod
    def player_user_prompt(summaries, history_context, score_string):
        return (
            f"------Your summaries of the game so far -------------"
            f"\n{summaries}\n\n"
            f"---------------------------------------------------------------------"
            f"Most recent rounds in full:\n{history_context}\n\n"
            f"---------------------------------------------------------------------"
            f"---------------------------------------------------------------------"
            f"Current scores: {score_string}"
            f"\n\nYour Turn:")
    
    
    
    @classmethod
    def player_system_prompt(self, agent, gameBoard):
        # Format Life Lessons as a bulleted list (Clean Readability)
        if agent.life_lessons:
            lessons_str = "\n".join([f"- {lesson}" for lesson in agent.life_lessons])
        else:
            lessons_str = "- None yet. I am a blank slate."

        return (
            f"You are {agent.name}.\n\n"
            f"{gameBoard.context_builder.get_dashboard_string(agent.name)}\n\n"
            
            f"=== YOUR PROFILE ===\n"
            f"Persona: {agent.persona}\n"
            f"Speaking Style: {agent.speaking_style}\n\n"
            
            f"=== LIFE LESSONS ===\n"
            f"Use these past learnings to guide your current behavior:\n"
            f"{lessons_str}\n\n"
            
            f"=== INTERNAL MONOLOGUE ===\n"
            f"Current Strategy: {agent.strategy_to_win}\n"
            f"Calculated Odds: {agent.mathematical_assessment}\n"
        )

