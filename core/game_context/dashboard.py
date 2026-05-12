class Dashboard:
    
    @classmethod 
    def append_scoreboard(cls, dash, agent_scores, agent_name, game_over):
       
        sorted_scores = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_scores[0][1] if sorted_scores else 0
        leaders = [name for name, score in agent_scores.items() if score == max_score]
        
        dash.append(cls.header("SCOREBOARD"))
        dash.append("(LIVE SCORES: updated each turn — already reflect every event shown below.)")
        for name, score in sorted_scores:
            marker = " <-- YOU" if name == agent_name else ""
            dash.append(f"- {name}: {score} points{marker}")
        
      
            
        
            
        # --- Status string --- #
        dash.append("") 
        if game_over:
            dash.append(f"STATUS: You have already been eliminated from the game. You are now an observer. ")
        else:
            my_score = agent_scores[agent_name]
            is_leader = agent_name in leaders
            points_behind = max_score - my_score

            if is_leader:
                if my_score > 0:
                    if len(leaders) > 1:
                        tied_with = [l for l in leaders if l != agent_name]
                        dash.append(f"STATUS: Tied for 1st.")
                    else:
                        dash.append("STATUS: You are winning.")
            else:
                dash.append(f"STATUS: You are {points_behind} points behind the leader.")

        
    
    @classmethod
    def header(cls, string):
        return(f"=== {string} ===")
    
    @classmethod
    def render(cls, agent, game_board) -> str:
        agent_name = agent.name
        game_over = agent.game_over
        agent_scores = dict(game_board.agent_scores)
        dash = []
        
        cls.append_scoreboard(dash, agent_scores, agent_name, game_over)
        
        removed_agent_names = game_board.phase_runner.removed_agent_names()
        if removed_agent_names:
            dead_str = ", ".join(removed_agent_names) if removed_agent_names else "None"
            dash.append(f"EVICTED PLAYERS: {dead_str} \n")
        
        if not game_over:
            dash.append(cls.header("PHASE PROGRESS"))
            dash.append(game_board.phase_runner.get_phase_progress_string())
            
        return "\n".join(dash)
    
