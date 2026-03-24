from gameplay_management.game_targeted.game_targeted_choice import *


class GameTargetedChoiceSacrifice(GameTargetedChoice):
    
    @classmethod
    def display_name(cls, cfg):
        return "Sacrificer"

    @classmethod
    def rules_description(cls, cfg):
        return "Use your own points to hurt another player"
    
    def run_game(self):
        self.run_game_sacrifice_points()
        
    def run_game_sacrifice_points(self):
        
        # 1. Define Flavor & Rules
        game_intro = (
            f"This is a game of self-sacrifice, of sabotage... "
            f"In this round, you can SPEND your own points to damage another player. "
            f"For every 1 point you spend, your target also loses a point! "
            f"The minimum points a player can have is zero-  don't spend points trying to get them to negative points."
            f"You can choose to pass if you want to save your strength."
        )
        
        player_intro = "{player_name}! You have the floor. Will you sabotage someone, or stay safe?"
        
        game_instruction = (
            "Decide if you want to attack. If yes, choose a target and an amount to spend. "
            "If no, choose 'Pass' as the target."
        )
        
        def sacrifice_points_model(player):
            my_score = self.gameBoard.get_agent_score(player.name) 
            if my_score <= 0:
                error_response = (f"{player.name} has no points, so has no choice but to sit this one out.")
                return self.get_error_model(error_response)
            targets = [name for name in self.gameBoard.agent_names() if name != player.name]
            targets.append("Pass") 
            action_fields = self._choose_name_field(targets, "Choose a player to attack, or 'Pass'.")
            spend_field_desc = (
                f"How many of your own points will you spend? You have {my_score} points. Your target player can't go into negative points, so don't waste points."
                f"Enter 0 if passing."
            )
            
            action_fields["points_to_spend"] = (
                int, 
                Field(description=spend_field_desc)
            )

            # Nudge: Show the scoreboard 
            scores_str = ", ".join([f"{k}: {v}" for k,v in self.gameBoard.agent_scores.items()])
            nudge = (
                f"Reminder- attacking a player with no points has no effect. Current scores: {scores_str}. "
            )
            
            return DynamicModelFactory.create_model_(
                agent=player,
                model_name="SabotageModel",
                action_fields=action_fields,
                additional_thought_nudge=nudge
            )

        def sacrifice_points_logic(player, target_agent, response):
            
            spent = response.points_to_spend
            target_name = getattr(response, GamePromptLibrary.model_field_choose_name, None)
            normalized_target = self._normalize_target_string(target_name)
            
            if normalized_target == "pass" or spent <= 0:
                return (
                    f"{player.name} chooses mercy (or cowardice?) and passes. No blood is shed.",
                    player # Player reacts to their own pass
                )

            if not target_agent or target_agent.name == player.name:
                return (
                    GamePromptLibrary.invalid_target_message.format(
                        player_name=player.name,
                        target_name=target_name,
                    ),
                    player
                )
            
            # Handle Valid Attack
            player_score = self.gameBoard.get_agent_score(player.name)
            victim_score = self.gameBoard.get_agent_score(target_agent.name)
            actual_spend = max(0, min(spent, player_score)) 
            damage = min(victim_score, actual_spend) #capped at the actual damange (they love to attack someone with no points)
            
            if actual_spend == 0: #This should should come from the response sending 0- if they player has zero points that should be caught earlier
                 return (f"{player.name} tried to attack but with no points to spend! It fizzles out.", player)
            if victim_score == 0:
                return (f"{target_agent.name} has no points, so the attack does nothing. Perhaps just to make a point?", player)
                
            # 2. Execute the Trade
            self.gameBoard.append_agent_points(player.name, -actual_spend) 
            self.gameBoard.append_agent_points(target_agent.name, -damage)
            
            result_host_string = (
                f"BRUTAL! {player.name} sacrifices {actual_spend} of their own points... "
                f"to crush {target_agent.name} for {damage} damage! "
                f"{target_agent.name}, wow... this must sting!"
            )
            
            return result_host_string, target_agent # Target reacts to the pain

        # 4. Run it
        self.run_targeted_round(
            game_intro, 
            player_intro, 
            game_instruction, 
            sacrifice_points_logic, 
            sacrifice_points_model,
            False
        )
        

