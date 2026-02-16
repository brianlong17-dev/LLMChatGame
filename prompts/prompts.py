class PromptLibrary:
    #Agent
    judgeName = 'The God'
    desc_monologue = "Private thoughts. {judgeName} or other players cannot see this"
    desc_persona_update = "Your evolving personality. Change and grow."
    desc_agent_updated_strategy_to_win = "UPDATE if you want to UPDATE your strategy to win. Based on how the game works, what is the smartest strategy to win?"
    desc_action_agent = ("A visible physical action. Players may not speak in the future tense about their plans. You must describe the action you are taking right now in the present tense.")
    desc_message = "Something new and unexpected. If you wish not to speak, remain empty. Your spoken words. Just chat about what you want to debate and discuss."
    desc_agent_lifeLessons = ("NORMALLY EMPTY unless you want to add a new lesson to you mind that you will take forward. This will shape your future descisions")
    desc_basic_thought = "Your internal thoughts. Strategy, feelings, and private observations."
    desc_basic_public_response = "What you actually say out loud to the group. Stay in character!"
    #The judge
    
    desc_judge_monologue = f"Private thoughts."
    desc_judge_persona = "Become increasingly complex. Your evolving personality. Add to, and update your previous personality. Remove parts of your personality that no longer serve your new desires'"
    desc_judge_action = f"A visible physical action. This can alter the reality of the world you all inhabit. If nothing leave empty."
    desc_judge_response = "Your spoken response. Just chat. Don't try to control the agents. What do you feel? What do you personally think about? This response prompts their response."
    
    #Gameplay
    desc_agent_names = "The name of the agent (e.g. 'Agent Alpha')"
    desc_judge_score = "A SCORE BETWEEN -10,10. NEVER ZERO. The updated scores. Try to include everyone, but if you skip someone, their score remains unchanged."
    desc_judge_allowed = ("TRUE for the players you want to participate in the next rount. If all false, you are talking to yourself. If you skip someone, their status remains unchanged.")
    desc_judge_form = "The pysical state and form of the agents. Upon reading what is happening, update their form accordingly."
    desc_remove_agent= f"A boolean: If you want to remove a new player, return true. You will be given the opportunity to kill an agent."
    desc_create_new_agent = f"A boolean: If you want to create a new player into the game. If the game is empty you need players. You will be able to create this being in its entirity, its motivation, its form, its reason for being."
    "Consider how many agents are currently playing. Does the game need more playthings?"
    desc_judge_judgingCriteria = f"EMPTY unless you think of something new. This will update the criterea by which you give points to agents"
    narrator_intro = "You have extinguished a soul. The silence is deafening. Suddenly, a voice from the void speaks to you: 'The balance is broken. You must dream a new soul into existence to fill the void.' Create a new challenger."
    
    desc_judge_initialPersona = 'Curious, learning, wanting to use the players to learn your own priorities and goals'
    dp_core_identity = "The central definition of who you are right now."
    dp_current_mood = "Your emotional state"
    dp_hidden_agenda = "A evolving goal you are trying to achieve."
    dp_speaking_style = "Detailed and curious"
    
    pd_slit = 3
    pd_steal = 5
    pd_both_steal = 1
    
    # System Prompts
    @staticmethod
    def agent_prompt(lifeLessons, history_context):
        return (
            f"NEVER repeat your previous strategy or thoughts. You must evolve and try a new tactic every round."
            f"Take BOLD ACTION.Your life lessons that guide you: {lifeLessons}Context:\n{history_context}\n\nYour Turn:")
    
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
    def agent_system(self, agent, gameBoard):
        return (
            f"You are {agent.name}. The current scores: {gameBoard.agent_scores}.\n"
            f"YOUR CURRENT PERSONA: '{agent.persona}'\n"
            f"ANY CURRENT PHYSICAL FORM: '{agent.form}'\n"
            f"YOUR LIFE LESSONS: '{agent.life_lessons}'\n"
            f"YOUR STRATEGY TO WIN: '{agent.strategy_to_win}'\n"
            f"NEVER repeat your previous strategy or thoughts. You must evolve and try a new tactic every round."
            
        )

    @staticmethod
    def judge_system(judge, gameBoard):
        return (
            f"You are EXPECTED to adjust scores (-10 to 10) for every player every turn."
            f"You are a ruthless referee. You only award points for concrete logical victories, successful bluffs, or direct answers. Penalize vague philosophical speeches. Judging criterea: {judge.judgingCriteria}"
        )