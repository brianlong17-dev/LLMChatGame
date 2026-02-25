class PromptLibrary:
    #Agent
    line_break = (f"\n{"="*50}")
    judgeName = 'The God'
    desc_persona_update = "Your evolving personality. Change and grow."
    desc_agent_updated_strategy_to_win = "UPDATE if you want to UPDATE your strategy to win. Based on how the game works, what is the smartest strategy to win?"
    desc_action_agent = ("A visible physical action. Players may not speak in the future tense about their plans. You must describe the action you are taking right now in the present tense.")
    desc_message = "Your spoken words. What will you say? Stay in character. What you say is revealed to the group"
    desc_agent_lifeLessons = ("A new lesson to you mind that you will take forward. This will shape your future descisions. Take key lessons only, so you don't cloud your decision making.")
    desc_agent_mathematicalAssessment = ("What's your assessment of the scoreboard and your place in it?")
    
    desc_basic_thought = "Your internal thoughts. Strategy, feelings, and private observations."
    desc_basic_public_response = "What you actually say out loud to the group. Stay in character!"
   
    #Gameplay
    desc_agent_names = "The name of the agent (e.g. 'Agent Alpha')"
    desc_remove_agent= f"A boolean: If you want to remove a new player, return true. You will be given the opportunity to kill an agent."
    desc_create_new_agent = (f"A boolean: If you want to create a new player into the game. If the game is empty you need players. You will be able to create this being in its entirity, its motivation, its form, its reason for being."
    f"Consider how many agents are currently playing. Does the game need more players?")
    desc_judge_judgingCriteria = f"EMPTY unless you think of something new. This will update the criterea by which you give points to agents"
    narrator_intro = "You have extinguished a soul. The silence is deafening. Suddenly, a voice from the void speaks to you: 'The balance is broken. You must dream a new soul into existence to fill the void.' Create a new challenger."
    
    desc_judge_initialPersona = 'Curious, learning, wanting to use the players to learn your own priorities and goals'
    dp_core_identity = "The central definition of who you are right now."
    dp_current_mood = "Your emotional state"
    dp_hidden_agenda = "A evolving goal you are trying to achieve."
    dp_speaking_style = "Detailed and curious"
    
    @staticmethod
    def final_words_prompt(gameBoard):
        history_context = gameBoard.get_full_context()
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
    def player_user_prompt( history_context):
        return (
            f"Consider the current phase, what round you're in, and what comes next- If there is an elimination coming up, who will be going home?"
            f"Context:\n{history_context}\n\n"
            f"---------------------------------------------------------------------"
            f"No matter what, say something with the intention of moving yourself forward. Be proactive, dive in, speak to get responses."
            f"---------------------------------------------------------------------"
            f"Your Turn:")
    
    
    
    @classmethod
    def player_system_prompt(self, agent, gameBoard):
        # Format Life Lessons as a bulleted list (Clean Readability)
        if agent.life_lessons:
            lessons_str = "\n".join([f"- {lesson}" for lesson in agent.life_lessons])
        else:
            lessons_str = "- None yet. I am a blank slate."

        return (
            f"You are {agent.name}.\n\n"
            f"{gameBoard.get_dashboard_string(agent.name)}\n\n"
            
            f"=== YOUR PROFILE ===\n"
            f"Persona: {agent.persona}\n"
            #f"Physical Form: {agent.form}\n\n"
            f"Speaking Style: {agent.speaking_style}\n\n"
            
            f"=== LIFE LESSONS ===\n"
            f"Use these past learnings to guide your current behavior:\n"
            f"{lessons_str}\n\n"
            
            f"=== INTERNAL MONOLOGUE ===\n"
            f"Current Strategy: {agent.strategy_to_win}\n"
            f"Calculated Odds: {agent.mathematicalAssessment}\n"
        )

    @staticmethod
    def judge_system(judge, gameBoard):
        return (
            f"You are EXPECTED to adjust scores (-10 to 10) for every player every turn."
            f"You are a ruthless referee. You only award points for concrete logical victories, successful bluffs, or direct answers. Penalize vague philosophical speeches. Judging criterea: {judge.judgingCriteria}"
        )