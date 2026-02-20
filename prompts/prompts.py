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
    desc_judge_score = "A SCORE BETWEEN -10,10. NEVER ZERO. The updated scores. Try to include everyone, but if you skip someone, their score remains unchanged."
    desc_judge_allowed = ("TRUE for the players you want to participate in the next rount. If all false, you are talking to yourself. If you skip someone, their status remains unchanged.")
    desc_judge_form = "The pysical state and form of the agents. Upon reading what is happening, update their form accordingly."
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
    
    
    
    # System Prompts
    @staticmethod
    def player_user_prompt(lifeLessons, history_context):
        return (
            f"Consider the current phase, what round you're in, and what comes next- If there is an elimination coming up, who will be going home?"
            f"Context:\n{history_context}\n\n"
            f"Your life lessons that guide you: {lifeLessons}"
            f"---------------------------------------------------------------------"
            f"No matter what, say something with the intention of moving yourself forward. Be proactive, dive in, speak to get responses."
            f"---------------------------------------------------------------------"
            f"Your Turn:")
    
    @staticmethod
    def judge_user(judge, game_board):
        template = (
            "### JUDGE PROTOCOL ###\n"
            "Current Persona: {persona}\n"
            "Life Lessons: {lessons}\n"
            "Current Agent Ratings: {scores}\n\n"
            "Current Agent Forms: {agent_forms}\n\n"
            "Current Agent Allowed to speak: {agent_allowed}\n\n"
            "### RECENT EXCHANGE ###\n"
            "{history}\n\n"
            "Based on the above, provide your monologue, actions, and spoken response."
        )
        
        return template.format(
            persona=judge.complex_persona,
            lessons=judge.life_lessons,
            scores=game_board.agent_scores,
            history=game_board.get_full_context(),
            agent_forms = game_board.agent_forms,
            agent_allowed = game_board.agent_response_allowed
        )
        
    
    @classmethod
    def player_system_prompt(self, agent, gameBoard):
        return (
            f"You are {agent.name}. The current scores: {gameBoard.agent_scores}.\n"
            f"{gameBoard.get_dashboard_string(agent.name)}\n" # I think this is currently way too much 
            f"YOUR CURRENT PERSONA: '{agent.persona}'\n"
            f"ANY CURRENT PHYSICAL FORM: '{agent.form}'\n"
            f"YOUR LIFE LESSONS: '{list(agent.life_lessons)}'\n"
            f"YOUR STRATEGY TO WIN: '{agent.strategy_to_win}'\n"
            f"Mathematical assessment of the scores: '{agent.mathematicalAssessment}'\n"
        )

    @staticmethod
    def judge_system(judge, gameBoard):
        return (
            f"You are EXPECTED to adjust scores (-10 to 10) for every player every turn."
            f"You are a ruthless referee. You only award points for concrete logical victories, successful bluffs, or direct answers. Penalize vague philosophical speeches. Judging criterea: {judge.judgingCriteria}"
        )