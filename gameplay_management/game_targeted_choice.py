from pydantic import Field, create_model
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary

class GameTargetedChoice(GameMechanicsMixin):
    def get_error_model(self, message: str):
    # This creates a NEW class where the default value is your specific message
        return create_model("Error", error_string=(str, message))
    
    def get_error_string(self, model_class):
        if GamePromptLibrary.model_field_error in model_class.model_fields:
            return model_class().error_string
        return None

    def _normalize_target_string(self, target: str):
        return str(target).strip().lower() if target is not None else ""

    def _clean_target_name(self, target: str):
        if target is None:
            return None
        cleaned = str(target).strip()
        return cleaned or None
    
    def run_targeted_round(self, game_intro, player_intro, game_instruction, logic_callback, response_model_callback, validate_name=True):
        self.gameBoard.host_broadcast(game_intro)
        available_agents = self._shuffled_agents()
        
        for player in available_agents:
            self.gameBoard.host_broadcast(player_intro.format(player_name=player.name))
            
            #---Generate model, check if error----#
            response_model = response_model_callback(player)
            error = self.get_error_string(response_model)
            if error:
                result_host_string = error
                player_for_reaction = player
                            
                
            else:
                response = player.take_turn_standard(game_instruction, self.gameBoard, response_model)
                self.publicPrivateResponse(player, response)
                
                target_name = getattr(response, GamePromptLibrary.model_field_choose_name)
                target_agent = self._agent_by_name(self._clean_target_name(target_name))
                
                if validate_name and (not target_agent or target_agent.name == player.name):
                    result_host_string = GamePromptLibrary.invalid_target_message.format(
                        player_name=player.name,
                        target_name=target_name,
                    )
                    player_for_reaction = player
                else:
                    # Execute the specific logic (Give vs Steal vs Sacrifice)
                    result_host_string, player_for_reaction = logic_callback(player, target_agent, response)
                    
            self.gameBoard.host_broadcast(result_host_string)
            reaction = self.respond_to(player_for_reaction, result_host_string)
            self.publicPrivateResponse(player_for_reaction, reaction)
    
    def run_game_give(self):
        points_amount = GamePromptLibrary.targeted_games_points
        game_intro = GamePromptLibrary.give_game_intro #really should this be merged with the game def.
        player_intro = GamePromptLibrary.give_game_player_intro
        game_instruction = f"Choose one player from to receive {points_amount} points. Explain why."
        
        
        def give_points_model(player):
            other_agent_names = [name for name in self.gameBoard.agent_names if name != player.name]
            action_fields = self._choose_name_field(other_agent_names, game_instruction) #player intro is not correct here
            return DynamicModelFactory.create_model_(player, model_name="GivePointsModel", action_fields=action_fields) 
            
        def give_points_logic(player, target_agent, _response): #response is only needed for subtraction
            result_host_string = f"Yay! {player.name} chooses {target_agent.name}! They receive {points_amount} points."
            self.gameBoard.append_agent_points(target_agent.name, points_amount)
            return(result_host_string, target_agent)
        
        self.run_targeted_round(game_intro, player_intro, game_instruction, give_points_logic, give_points_model)
        
    def run_game_steal(self):
        points_amount = GamePromptLibrary.targeted_games_points
        game_intro = (f"Well, it's time to lay down your mark.. "
        f"In this round, you will get to STEAL. Whatever player you pick, you will receive {points_amount} points... and they will LOSE them! "
        f"If you choose a player with less than {points_amount} points, their points wont go below zero, and you won't receive the full {points_amount} points." )
        player_intro = ("{player_name}! You're up- what player are you choosing to steal from, and why?") #can format this later?
        game_instruction = (f"Choose one player from to steal {points_amount} points from. Explain why."
            f"If you steal from a player with less than {points_amount}, you'll only get whatever points the have, maybe zero.")
        thought_nudge = (f"Current scores: {self.gameBoard.agent_scores}"
            f"If you try to steal from someone with 0 points, you essentially pass.")
        
        def steal_points_model(player):
            other_agent_names = [name for name in self.gameBoard.agent_names if name != player.name]
            action_fields = self._choose_name_field(other_agent_names, game_instruction)
            return DynamicModelFactory.create_model_(
                agent=player, 
                model_name="StealPointsModel", 
                action_fields=action_fields,
                additional_thought_nudge=thought_nudge
            )
        def steal_points_logic(player, target_agent, _response):
            current_victim_points = self.gameBoard.get_agent_score(target_agent.name)
            actual_steal = min(points_amount, max(0, current_victim_points))
            
            if actual_steal <= 0:
                result_host_string = (
                    f"Awkward... {player.name} tried to steal from {target_agent.name}, "
                    f"but they have empty pockets! No points changed hands."
                )
                player_for_reaction = player 
            else:
                result_host_string = (
                    f"Oooooh! {player.name} steals from {target_agent.name}! "
                    f"{player.name} gains {actual_steal} points, and {target_agent.name} loses them!"
                )
                player_for_reaction = target_agent
            
            # Update the board
            self.gameBoard.append_agent_points(player.name, actual_steal)
            self.gameBoard.append_agent_points(target_agent.name, -actual_steal)
            return result_host_string, player_for_reaction
        self.run_targeted_round(game_intro, player_intro, game_instruction, steal_points_logic, steal_points_model)
        
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
            targets = [name for name in self.gameBoard.agent_names if name != player.name]
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
        
