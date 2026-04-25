import random
from gameplay_management.game_cycle.game_cycle import CycleRound
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class GameCircle(CycleRound):

    @classmethod
    def display_name(cls, cfg):
        return "The Circle"

    SURVIVORS_BONUS = 5
    SHOT_PENALTY = 2

    @classmethod
    def rules_description(cls, cfg):
        shot_pts = "a point" if cls.SHOT_PENALTY == 1 else f"{cls.SHOT_PENALTY} points"
        bonus_pts = "a point" if cls.SURVIVORS_BONUS == 1 else f"{cls.SURVIVORS_BONUS} points"
        return (
            "Players stand in a circle. Each game cycle, one player receives a gun and another receives a shield. "
            "The shield holder picks one other player to protect. The gun holder then shoots one unprotected player. "
            f"Being shot costs you {shot_pts} (given to the shooter) and removes you from the circle. "
            f"The last 3 standing earn {bonus_pts} each."
        )

    def _quick_get_in(self, shield_holder, unprotected_pool, gun_holder_name):
        self.gameBoard.host_broadcast(f"{shield_holder.name}, who do you choose! ")
        pool_names = [a.name for a in unprotected_pool] + [shield_holder.name]
        action_fields = self._choose_name_field([a.name for a in unprotected_pool], "Choose one player to protect behind your shield.")
        model = DynamicModelFactory.create_model_(shield_holder, action_fields=action_fields, 
                                public_response_prompt = "What do you yell at the person you've chosen!",
                                additional_thought_nudge = "Who do you want to protect? Who is most at danger from the shooter? Would be a valuable ally? To whom do you owe a favor?")
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
        
    def _take_shot(self, gun_holder, unprotected_pool):
        targetable_names = [a.name for a in unprotected_pool] + [gun_holder.name]  # includes gun_holder themselves
        action_fields = self._choose_name_field(targetable_names, "Choose who to shoot.", field_name = 'target_choice')
        if self.double_shot:
            action_fields = action_fields | self._choose_name_field(targetable_names, "Choose who to shoot with second bullet.", field_name = 'target_choice_2')
        model = DynamicModelFactory.create_model_(gun_holder, action_fields=action_fields, 
                                                  public_response_prompt = "What you say to the group AFTER the shot goes and the smoke clears. It can be a smooth one liner, or remorseful plea for forgiveness. ",
                                                  additional_thought_nudge = "Who do you want to shoot? Whose points do you want? What will you say? Do you want to intimidate the group or make them feel sorry for you? ")
        other_names = self.format_list([a.name for a in unprotected_pool])
        bullet_string = "You have two bullets!" if self.double_shot else "You have one bullet!"
        result = gun_holder.take_turn_standard(f"YOU have the gun. {bullet_string} The players behind the shield are safe. {other_names} are all potential targets. ", self.gameBoard, model)
        shot_names = [result.target_choice.strip()]
        if self.double_shot:
            shot_names += [result.target_choice_2.strip()]
        
        self.gameBoard.handle_public_private_output(gun_holder, result)
        valid_shots = []
        for shot_name in shot_names:
            if shot_name not in targetable_names:
                self.gameBoard.host_broadcast(f"Oh no... {shot_name} was an invalid choice... The bullet flies away! ")
            else:
                valid_shots.append(shot_name)
        return valid_shots

    def _intro_message(self):
        shot_string = "one unprotected player" if not self.use_double_shots else "one or two unprotected players"
        
        return(
            "Welcome to THE CIRCLE. "
            "\nYou will stand in a circle, and each game cycle "
            "one player will get a GUN- and another a shield. "
            "The shield holder may protect ONE other player. "
            f"The gun holder will then shoot {shot_string} — the victim leaves the circle, and the shooter takes {self.points_string(self.SHOT_PENALTY)} of their points. "
            f"Last 3 standing earn {self.points_string(self.SURVIVORS_BONUS)}."
        )
    
    def _assign_gun_and_shield(self, circle, cycle_num):
        gun_holder = random.choice(circle)
        shield_holder = random.choice([a for a in circle if a != gun_holder])
        announcement = f"Cycle {cycle_num}:\n{gun_holder.name} has the GUN. {shield_holder.name} has the SHIELD. "
        if self.double_shot:
            announcement += "\nThis time they have 2 bullets, so 2 are at risk! "
        self.gameBoard.host_broadcast(announcement)
        return gun_holder, shield_holder

    def _make_pleas(self, unprotected_pool, gun_holder_name, shield_holder_name):
        for player in unprotected_pool:
            other_names = self.format_list([a.name for a in unprotected_pool if a != player])
            
            user_content_prompt = (f"{gun_holder_name} has the gun and is about to shoot. "
            f"{shield_holder_name} has the SHIELD. - they can only take one other person behind the shield. You, {other_names} are all in danger. "
            f"This is your only opportunity to plead to both! ")
            public_response_prompt = "Do you stay silent, and hope to be ignored? Or do you speak up and plead? Your public response to them both, and to be heard by the group. "
            private_thoughts_prompt = "Do you protect yourself? Can you remind them of alliance? What is the best strategy here? Is it better to stay silent? "
            
            self._basic_turn(player, user_content_prompt, public_response_prompt, 
                             private_thoughts_prompt=private_thoughts_prompt, optional = True)
       
        
    def _handle_shot_choice(self, circle, shield_holder, gun_holder, shot_names):
        if not shot_names:
            self.gameBoard.host_broadcast(f"{gun_holder.name} fails to hit a target, and so is removed from the circle!")
            circle.remove(gun_holder)
            return

        double_tapped = self.double_shot and len(shot_names) == 2 and shot_names[0] == shot_names[1]
        shot_names = list(dict.fromkeys(shot_names))
        for shot_name in shot_names:
            if shot_name == gun_holder.name:
                host_response = f"Oh my god... {gun_holder.name} shot themselves--! I don't believe it! "
                self.gameBoard.host_broadcast(host_response, delay = 1)
                player_to_remove = gun_holder

            else:
                shot_agent = next((a for a in circle if a.name == shot_name), None)
                if double_tapped:
                    self.gameBoard.host_broadcast(f"{gun_holder.name} shoots {shot_name} twice! They're trying to take double the points!")
                else:
                    self._host_respond_shooting(gun_holder.name, shot_name)
                player_to_remove = shot_agent

            # ── Points and removal ──
            if player_to_remove != gun_holder:
                multiplier = 2 if double_tapped else 1
                points = self.SHOT_PENALTY * multiplier
                self.gameBoard.append_agent_points(player_to_remove.name, -points)
                self.gameBoard.append_agent_points(gun_holder.name, points)
                self._host_broadcast(f"{gun_holder.name} + {points} points, {player_to_remove.name} - {points} points.")

            circle.remove(player_to_remove)
            survivors = [a for a in circle if a != gun_holder and a != shield_holder]
            if self.cfg().circle_get_shot_reactions:
                self._host_broadcast("Now for some reactions...")
                random_survivor = random.choice(survivors)
                #survivors = [random_survivor]
                for survivor in survivors:
                    react_prompt = f"{player_to_remove.name} has been shot. React to what just happened- or stay silent."
                    self._basic_turn(survivor, react_prompt, "Your reaction.", 
                                 optional = True)

   
    def run_game(self):
        self._cycle_game_setup()
        circle = list(self._shuffled_agents())
        cycle_num = 0
        self.use_double_shots = self.cfg().use_double_shots

        #Intro message
        #self.double_shot = use_double_shots
        self.gameBoard.host_broadcast(self._intro_message())
        self.gameBoard.host_broadcast(f"Remember! Being shot from the cirlce doesn't mean you're eliminated ! You're just out of this round. "
                                      "Everyone will still be in the game- this isn't an elimination. ")

        while len(circle) > 3:
            cycle_num += 1
            self.double_shot = (self.use_double_shots and (len(circle) > 5))
            # ── 1. Assign gun and shield randomly ──
            gun_holder, shield_holder = self._assign_gun_and_shield(circle, cycle_num)

            unprotected_pool = [a for a in circle if a != gun_holder and a != shield_holder]
            # -- 2. Plead your case
            self._make_pleas(unprotected_pool, gun_holder.name, shield_holder.name)
            
            # -- 3. Invite to shield
            unprotected_pool = self._quick_get_in(shield_holder, unprotected_pool, gun_holder.name)

            # -- 4. Shoot
            shot_names = self._take_shot(gun_holder, unprotected_pool)
            
            bang = "BANG! BANG! " if  self.double_shot else "BANG! "
            self.gameBoard.environment_broadcast(bang, delay = 1)
            
            # -- 5. Handle result
            self._handle_shot_choice(circle, shield_holder, gun_holder, shot_names)
            
            
            self._compress_round()
                
            
            
                
        # ── 6. Survivors bonus ──
        survivor_names = self.format_list([a.name for a in circle])
        self.gameBoard.host_broadcast(
            f"The circle is closed. {survivor_names} are the last ones standing! "
            f"Each survivor earns {self.SURVIVORS_BONUS} bonus points."
        )
        for agent in circle:
            self.gameBoard.append_agent_points(agent.name, self.SURVIVORS_BONUS)

        self._cycle_game_teardown()

    #######################
    # 
    #-----Output methods-----
    #
    #######################
            
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
      
