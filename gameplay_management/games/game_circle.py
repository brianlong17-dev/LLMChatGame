import random
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class GameCircle(BaseRound):

    @classmethod
    def display_name(cls, cfg):
        return "The Circle"

    @classmethod
    def rules_description(cls, cfg):
        return (
            "Players stand in a circle. Each round, one player receives a gun and another receives a shield. "
            "The shield holder picks one other player to protect. The gun holder then shoots one unprotected player. "
            "Being shot costs you a point (given to the shooter) and removes you from the circle. "
            "The last 3 standing earn 3 bonus points each."
        )

    @classmethod
    def is_game(cls):
        return True

    def _basic_turn(self, agent, user_content_prompt, public_response_prompt, private_thoughts_prompt = None, optional = True):
        
        basic_model = DynamicModelFactory.create_model_(agent, "basic_turn", public_response_prompt = public_response_prompt, private_thoughts_prompt = private_thoughts_prompt, optional=optional)
        result = agent.take_turn_standard(user_content_prompt, self.gameBoard, basic_model)
        if optional:
            public_response = result.public_response
            if not public_response:
                print("BEEP BEEP BEEP")
        else:
            public_response = True
            
        if public_response:
            self.gameBoard.handle_public_private_output(agent, result)
            
    def _host_respond_shooting(self, shooter_name, shot_name):
        responses = [
            f"{shooter_name} pulls the trigger... {shot_name} is hit!",
            f"{shot_name} goes down! {shooter_name} got them!",
            f"And {shooter_name} shoots... {shot_name}! They're out of the circle!",
            f"A cold choice. {shooter_name} takes out {shot_name}.",
            f"{shot_name} didn't see it coming. {shooter_name} made their move.",
        ]
        self.gameBoard.host_broadcast(random.choice(responses))

    def _shield_host_response(self, shield_holder_name, choice_name):
        responses = [
            f"{shield_holder_name} chooses {choice_name}! They hide together behind the shield!",
            f"{choice_name} quick! Get behind {shield_holder_name}'s shield!",
            f"Wow! {shield_holder_name} has chosen {choice_name}... just in the nick of time!",
        ]
        self.gameBoard.host_broadcast(random.choice(responses))
        
    def _quick_get_in(self, shield_holder, unprotected_pool, gun_holder_name):
        
        pool_names = [a.name for a in unprotected_pool]
        action_fields = self._choose_name_field([a.name for a in unprotected_pool], "Choose one player to protect behind your shield.")
        model = DynamicModelFactory.create_model_(shield_holder, action_fields=action_fields, 
                                public_response_prompt = "What do you yell at the person you've chosen!",
                                additional_thought_nudge = "Who do you want to protect? Who is most at danger from the shooter? Whould be a valuable ally? To whom do you owe a favor?")
        user_content = (f"{gun_holder_name} has a gun and is about to shoot! You're already behind a shield. "
                        f"There's room for one more... {self.format_list(pool_names)} are all in danger- who will you call to protect? ")
        result = shield_holder.take_turn_standard(user_content, self.gameBoard, model)
        self.gameBoard.handle_public_private_output(shield_holder, result)
        protected_name = getattr(result, GamePromptLibrary.model_field_choose_name).strip()
        if protected_name in pool_names:
            self._shield_host_response(shield_holder.name, protected_name)
            return [a for a in unprotected_pool if a.name != protected_name]
        else:
            self.gameBoard.host_broadcast(f"Oh no! {protected_name} was an invalid choice! {shield_holder.name} will be alone behind the shield!")
            return unprotected_pool
        
        
    def _take_shot(self, gun_holder, unprotected_pool, double_shot):
        targetable_names = [a.name for a in unprotected_pool] + [gun_holder.name]  # includes gun_holder themselves
        action_fields = self._choose_name_field(targetable_names, "Choose who to shoot.", field_name = 'target_choice')
        if double_shot:
            action_fields = action_fields | self._choose_name_field(targetable_names, "Choose who to shoot with second bullet.", field_name = 'target_choice_2')
        model = DynamicModelFactory.create_model_(gun_holder, action_fields=action_fields, 
                                                  public_response_prompt = "What you say to the group AFTER the shot goes and the smoke clears. It can be a smooth one liner, or remorsful plea for forgiveness. ",
                                                  additional_thought_nudge = "Who do you want to shoot? Whose point to you want? What will you say? Do you want to intimidate the group or make them feel sorry for you? ")
        other_names = self.format_list([a.name for a in unprotected_pool])
        bullet_string = "You have two bullets!" if double_shot else "You have one bullet!"
        result = gun_holder.take_turn_standard(f"YOU have the gun. {bullet_string} The players behind the shield are safe. {other_names} are all potential targets. ", self.gameBoard, model)
        shot_names = [result.target_choice.strip()]
        if double_shot:
            shot_names += [result.target_choice_2.strip()]
        
        self.gameBoard.handle_public_private_output(gun_holder, result)
        valid_shots = []
        for shot_name in shot_names:
            if shot_name not in targetable_names:
                self.gameBoard.host_broadcast(f"Oh no... {shot_name} was an invalid choice... The bullet flies away! ")
            else:
                valid_shots.append(shot_name)
        return valid_shots
        
    def run_game(self):
        circle = list(self._shuffled_agents())
        SURVIVORS_BONUS = 5
        SHOT_PENALTY = 2
        round_num = 0
        double_shot = False

        self.gameBoard.host_broadcast(
            "Welcome to THE CIRCLE. You will stand in a circle. "
            "Each round, one of you gets a gun, and one of you gets a shield. "
            "The shield holder may protect ONE other player. "
            "The gun holder will then shoot one unprotected player — they lose a point, the shooter gains one, and they leave the circle. "
            "Last 3 standing earn 3 bonus points."
        )
        
        

        while len(circle) > 3:
            round_num += 1
            double_shot = (len(circle) > 5)
            

            # ── 1. Assign gun and shield randomly ──
            gun_holder = random.choice(circle)
            shield_holder = random.choice([a for a in circle if a != gun_holder])
            announcement = f"Round {round_num}. {gun_holder.name} has the GUN. {shield_holder.name} has the SHIELD. "
            if double_shot:
                announcement += "This time they have 2 bullets, so 2 are at risk! "

            self.gameBoard.host_broadcast(announcement)
            
            unprotected_pool = [a for a in circle if a != gun_holder and a != shield_holder]
            for player in unprotected_pool:
                other_names = self.format_list([a.name for a in circle if a != player])
                
                user_content_prompt = (f"{gun_holder.name} has the gun and is about to shoot!  {shield_holder.name} has the SHIELD."
                f"They can only take one other person behind the shield. You, {other_names} are all in danger. "
                f"This is your only opportunity to plead to both! ")
                #still so unclear when the user content prompt is injected
                public_response_prompt = "Your public response to them both, and to be heard by the group. "
                private_thoughts_prompt = "Do you protect yourself? Can you remind them of alliance? What is the best strategy here? "
                self._basic_turn(player, user_content_prompt, public_response_prompt, private_thoughts_prompt=private_thoughts_prompt, optional=False)
            
            self.gameBoard.host_broadcast(f"{shield_holder.name}, who do you choose! ")
            unprotected_pool = self._quick_get_in(shield_holder, unprotected_pool, gun_holder.name)
            


            
            shot_names = self._take_shot(gun_holder, unprotected_pool, double_shot)
            #if shot name is gunholder!
            #TODO this needs a new output type-
            bang = "BANG! BANG! " if double_shot else "BANG! "
            
            
            self.gameBoard.host_broadcast(bang, delay = 1)
            
            
            #here we have to filter double names and output a reaction
            if not shot_names:
                self.gameBoard.host_broadcast(f"{gun_holder.name} fails to hit a target, and so is removed from the circle!")
                circle.remove(gun_holder)
                continue

            shot_names = list(dict.fromkeys(shot_names))
            for shot_name in shot_names:
                if shot_name == gun_holder.name:
                    host_response = f"Oh my god... {gun_holder.name} shot themselves--! I don't believe it! "
                    self.gameBoard.host_broadcast(host_response, delay = 1)
                    player_to_remove = gun_holder
                    
                else:
                    shot_agent = next((a for a in circle if a.name == shot_name), None)
                    self._host_respond_shooting(gun_holder.name, shot_name)
                    player_to_remove = shot_agent

                # ── Points and removal ──
                if player_to_remove != gun_holder:
                    self.gameBoard.append_agent_points(player_to_remove.name, -SHOT_PENALTY)
                    self.gameBoard.append_agent_points(gun_holder.name, SHOT_PENALTY)

                circle.remove(player_to_remove)

            if False:
                survivors = [a for a in circle if a != gun_holder and a != shield_holder]
                for agent in survivors:
                    react_prompt = f"{player_to_remove.name} has been shot. React to what just happened."
                    self._basic_turn(agent, react_prompt, "Your reaction.", optional=True)
                

        # ── 6. Survivors bonus ──
        survivor_names = self.format_list([a.name for a in circle])
        self.gameBoard.host_broadcast(
            f"The circle is closed. {survivor_names} are the last ones standing! "
            f"Each survivor earns {SURVIVORS_BONUS} bonus points."
        )
        for agent in circle:
            self.gameBoard.append_agent_points(agent.name, SURVIVORS_BONUS)
