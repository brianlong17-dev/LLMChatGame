import random
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory

if TYPE_CHECKING:
    from agents.player import Debater

@dataclass
class Mob:
    leader: "Debater"
    target: str  # target's name
    followers: list["Debater"]

class GameMob(BaseRound):
    
    """ This is a first pass at the game
    The mechanics dont really work- 
    I think consolodating the mobs isnt a good choice. 
    They should see the mobs 
    and be able to choose to leave or stay.
    If you're leader you take your followers with you.
    Anyway - the leaders need to pitch.
    Also i thought of a bribing mechanic - where if player B is targetted .
    the can make a pot of their points to whoever moves over.
    """

    PASS = "Pass"
    STAY = "Stay"
    
    PARALLEL_CHANGING = True
    RECONSIDER_POINTS = 2

    @classmethod
    def display_name(cls, cfg):
        return "Mob Mentality"

    @classmethod
    def rules_description(cls, cfg):
        return (
            "Players can nominate themselves as mob leaders and announce a target. "
            "All other players secretly pledge to a mob. Smaller mobs are disbanded and members choose again. "
            "This repeats until two mobs remain. The larger mob wins — the target loses ALL their points, "
            "split among the winning mob members. In a tie, each target loses half."
        )
        
    ####################
    #
    # --- Narration ---#
    #
    ####################

    def _react_to_mob_initiation(self, agent, mob):
        target_name = f': {self.PASS}' if not mob else f" targets {mob.target}"
        self._host_broadcast(f"{agent.name}{target_name}")
        
      
    def _mob_label(self, mob, *, incl_followers=False, target_label='->'):
        follower_str = f" ({len(mob.followers)})" if incl_followers else ""
        return f"{mob.leader.name} {target_label} {mob.target}{follower_str}"

    def _mobs_string(self, mobs):
        return "\n".join(f"- {self._mob_label(mob, incl_followers=True)}" for mob in mobs)

    def _announce_mobs_initial(self):
        output_string = f"After the nomination round, {len(self.mobs)} mobs have been formed: \n"
        for mob in sorted(self.mobs, key=lambda m: m.target):
            output_string += f"{self._mob_label(mob)}\n"
        output_string += "\n"
        self._host_broadcast(output_string)
            
    def _announce_mobs(self):
        output_string = "Our mobs as they now stand: \n"
        for mob in self._sorted_mobs():

            follower_names = self.format_list([f.name for f in mob.followers]) if mob.followers else "no followers yet"
            followers_name_string =  f" — members: {follower_names}" if mob.followers else ""
            output_string += f"{self._mob_label(mob, incl_followers=True)}{followers_name_string}\n"
        self._host_broadcast(output_string)
            

    def _sorted_mobs(self):
        return sorted(self.mobs, key=lambda m: len(m.followers) + 1, reverse=True)
    
    @classmethod
    def is_game(cls):
        return True

    def _force_choice(self, agent):
        
        questions = [f"{agent.name}, as an unwilling leader, who do you choose to target? ",
                     f"Unfortunately {agent.name}, the time to follow is over- now it's time to lead. Who will you target? ",
                     f"Some are born to lead, others... have leadership thrust upon them. {agent.name}, you time has come. Who will you target? "]
        self._host_broadcast_multiple_choice(questions)
        
        valid_targets = [a.name for a in self.agents if a.name != agent.name]
        action_fields = self.turn_manager.create_choice_field(
            "mob_choice",
            valid_targets,
            "You have been chosen as a mob leader. You must pick a target — no passing."
        )
        model = DynamicModelFactory.create_model_(
            agent,
            action_fields=action_fields,
            public_response_prompt="Announce your target to the group.",
            additional_thought_nudge="You have no choice but to lead. Who do you go after?"
        )
        self._host_broadcast(f"No one stepped up — {agent.name}, you've been drafted as a mob leader!")
        result = agent.take_turn_standard(
            f"You've been forced into leadership. You must choose a target: {self.format_list(valid_targets)}",
            self.gameBoard, model
        )
        self.gameBoard.handle_public_private_output(agent, result)
        choice = result.mob_choice.strip()
        if choice in valid_targets:
            return Mob(agent, choice, [])
        
        else:
            fallback = random.choice(valid_targets)
            self.private_system_message(agent, f"Invalid choice '{choice}' — {fallback} was assigned as your target.")
            return Mob(agent, fallback, [])

    

    def _force_mob_leaders(self):
        agents_to_choose = random.sample(self.agents, 2)
        self._host_broadcast(f"Since no one stepped up, {agents_to_choose[0].name} and {agents_to_choose[1].name} have been selected to be mob leaders.")
        for agent in agents_to_choose:
            mob = self._force_choice(agent)
            self._react_to_mob_initiation(agent, mob)
            self.mobs.append(mob)
        
    def _decide_to_be_leader(self, agent, other_agents):
        valid_targets = [a.name for a in other_agents if a.name != agent.name]
        choices = [self.PASS] + valid_targets

        action_fields = self.turn_manager.create_choice_field(
            "mob_choice",
            choices,
            ("Choose a player to TARGET. If you want to join someone elses mob, choose PASS. "
            "By choosing a name - you are choosing to lead a mob against this person. "
            "If you prefer to join someone else - choose pass- you can join their mob later. ")
            
        )
        model = DynamicModelFactory.create_model_(
            agent,
            action_fields=action_fields,
            public_response_prompt=(f"If you chose to lead a mob, declare your target. If you pass, leave this null. "
                                    "Give your initial pitch as to why others should join your mob. "),
            additional_thought_nudge=(
                "Should you step up as leader? Who is your biggest threat? "
                "Could you rally others against them? Remember — leaders earn double points if their mob wins, "
                "but you also paint a target on yourself. "
                "REMINDER - You are TARGETTING this person - not joining their mob. "
            )
        )
        user_content = (
            f"You can nominate yourself as a mob leader now. "
            f"Choose a target to mob, or pass to wait and join someone else's mob. "
            f"Valid targets: {self.format_list(valid_targets)}"
        )
        result = agent.take_turn_standard(user_content, self.gameBoard, model)
        choice = result.mob_choice.strip()
        if choice == self.PASS:
            return None
        
        elif choice in valid_targets:
            self.gameBoard.handle_public_private_output(agent, result)
            return Mob(agent, choice, [])
        else:
            self.private_system_message(agent, f"Invalid target choice '{choice}' — your nomination has been ignored.")
            return None
    
    def _choose_to_join_mobs(self, followers):
        tasks = [(follower,) for follower in followers]
        results = self._run_tasks(tasks, self._make_mob_choice)
        for follower, result in results:
            self._handle_mob_choice_response(follower, result)

    def _handle_mob_choice_response(self, follower, result):
        self.gameBoard.handle_public_private_output(follower, result, delay = 1)
        choice = result.mob_choice.strip()
        chosen_mob = next((m for m in self.mobs if self._mob_label(m, target_label='targetting') == choice), None)
        if not chosen_mob:
            chosen_mob = random.choice(self.mobs)
            self.private_system_message(follower, f"{follower.name} made an invalid choice '{choice}' — they have been randomly assigned to {self._mob_label(chosen_mob)}.")
        else:
            self._host_broadcast(f"{follower.name} has chosen to join {self._mob_label(chosen_mob)}")
        chosen_mob.followers.append(follower)


    def _make_mob_choice(self, follower, rejoining = False):
        choices = [self._mob_label(mob, target_label='targetting') for mob in self.mobs]
        action_fields = self.turn_manager.create_choice_field(
            "mob_choice",
            choices,
            "Choose which mob to join."
        )
        model = DynamicModelFactory.create_model_(
            follower,
            action_fields=action_fields,
            public_response_prompt="What do you say as you pledge to your chosen mob?",
            additional_thought_nudge="Who do you trust? Who do you think will win? Who is targeting your enemies?"
        )
        prompt = f"The following mobs have been formed:\n{self._mobs_string(self.mobs)}\nChoose one to join."
        if rejoining:
            rejoining_prompt = f"Your mob was the smallest and has been disbanded. Time to choose a new tribe. \n"
            prompt = prompt + rejoining_prompt
        result = follower.take_turn_standard(
            prompt,
            self.gameBoard, model
        )
        return follower, result

   
    def _consolidate_mobs(self):
        grouped = defaultdict(list)
        for mob in self.mobs:
            grouped[mob.target].append(mob)

        needs_consolidation = any(len(group) > 1 for group in grouped.values())
        if needs_consolidation:
            self._host_broadcast(
                "CONSOLIDATION - mobs with the same target will be merged. "
            )

        new_mobs = []
        for target, group in grouped.items():
            if len(group) == 1:
                new_mobs.append(group[0])
                continue
            output_string = f"We have {len(group)} mobs targeting {target}. "

            group.sort(key=lambda m: len(m.followers), reverse=True)
            top_count = len(group[0].followers)
            tied = [m for m in group if len(m.followers) == top_count]

            if len(tied) == 1:
                winner = tied[0]
                output_string += f"{winner.leader.name} had the most followers — they take control of the mob. "
            else:
                # Tiebreak by points
                tied.sort(key=lambda m: self.gameBoard.agent_scores[m.leader.name], reverse=True)
                top_points = self.gameBoard.agent_scores[tied[0].leader.name]
                points_tied = [m for m in tied if self.gameBoard.agent_scores[m.leader.name] == top_points]

                if len(points_tied) == 1:
                    winner = points_tied[0]
                    output_string += f"Two mobs were equal in size — but {winner.leader.name} has more points, so they take the lead. "
                    
                else:
                    winner = random.choice(points_tied)
                    self._host_broadcast(
                        f"As the top leaders had equal points, {winner.leader.name} was chosen at random to take command. "
                    )

            # Losing leaders become followers of the winner
            for mob in group:
                if mob is winner:
                    continue
                winner.followers.append(mob.leader)
                winner.followers.extend(mob.followers)
            output_string += f"The mob now has {len(winner.followers)} followers. \n"

            self._host_broadcast(output_string)
            new_mobs.append(winner)

        self.mobs = new_mobs

    def _split_points(self, mob):
        points_to_take = self.gameBoard.agent_scores[mob.target]
        self.gameBoard.append_agent_points(mob.target, -points_to_take)
        total_shares = len(mob.followers) + 2
        share = points_to_take // total_shares
        if share < 1:
            share = 1
            self._host_broadcast(
                f"{mob.target} didn't have enough points to go around — "
                f"each mob member earns 1 point, and {mob.leader.name} earns 2 as leader."
            )
        self.gameBoard.append_agent_points(mob.leader.name, share * 2)
        for follower in mob.followers:
            self.gameBoard.append_agent_points(follower.name, share)
        follower_names = self.format_list([f.name for f in mob.followers]) if mob.followers else "no followers"
        self._host_broadcast(
            f"{mob.target} loses {points_to_take} points. "
            f"{mob.leader.name} earns {share * 2} points as leader. "
            f"{follower_names} each earn {share} points."
        )
        return points_to_take
    
    def _disband_mob(self, mob):
        self._host_broadcast(f"{self._mob_label(mob)} is the smallest — they are disbanded.")
        free_agents = [mob.leader] + mob.followers
        self.mobs.remove(mob)
        self._host_broadcast(
            f"{self.format_list([a.name for a in free_agents])}, you are now free — choose a new mob."
        )
        for agent in free_agents:
            follower, result = self._make_mob_choice(agent, rejoining=True)
            self._handle_mob_choice_response(follower, result)
        
    def _make_pitch(self, free_agents):
        free_names = self.format_list([a.name for a in free_agents])
        self._host_broadcast(
            f"{free_names} — it's time to choose your side. But first, let's hear from the leaders."
        )
        for mob in self.mobs:
            self._host_broadcast_multiple_choice([
                f"{mob.leader.name}, as a mob leader, why should they join your mob targeting {mob.target}? Should they be afraid not to? ",
                f"{mob.leader.name} — all of a sudden you're in position of power- time to make your case. Why should the free agents join you?",
                f"The floor is yours, {mob.leader.name}. Should they join you?",
            ])
            self.turn_manager._basic_turn(
                mob.leader,
                f"{free_names} must now choose which mob to join.  Why should they join your mob targeting {mob.target}?",
                "Your pitch to the free agents.",
                optional=False
            )

        self._host_broadcast("And now — a word from the targets.")
        for mob in self.mobs:
            target = self._agent_by_name(mob.target)
            if target:
                self._host_broadcast_multiple_choice([
                    f"{target.name}, you're in a rough spot. What do you say to someone considering joining the mob against you?",
                    f"How does it feel, {target.name}? The mob is growing — do you have anything to say?",
                    f"{target.name} — now's your chance. Can you turn the tide?",
                ])
                self.turn_manager._basic_turn(
                    target,
                    f"{free_names} are considering joining the mob targeting you. This is your opportunity to plead your case. ",
                    "Your public words. ", 
                    optional=False
                )
        
    def _finale(self):
        #if they consolidate into one immediately
        if len(self.mobs) == 1:
            winner = self.mobs[0]
            
        else:
            mob_a, mob_b = self.mobs[0], self.mobs[1]
            size_a = len(mob_a.followers) + 1
            size_b = len(mob_b.followers) + 1

            self._host_broadcast(
                f"Two mobs remain: \n"
                f"- {self._mob_label(mob_a, incl_followers=True)}\n"
                f"- {self._mob_label(mob_b, incl_followers=True)}"
            )

            if size_a != size_b:
                winner, loser = (mob_a, mob_b) if size_a > size_b else (mob_b, mob_a)
                self._host_broadcast(
                    f"{self._mob_label(winner)} is the larger mob — they win!"
                )
            else:
                # tiebreak by leader points
                score_a = self.gameBoard.agent_scores[mob_a.leader.name]
                score_b = self.gameBoard.agent_scores[mob_b.leader.name]
                if score_a != score_b:
                    winner, loser = (mob_a, mob_b) if score_a > score_b else (mob_b, mob_a)
                    self._host_broadcast(
                        f"It's a tie on size — but {winner.leader.name} has more points and takes command of the win!"
                    )
                else:
                    winner, loser = random.choice([(mob_a, mob_b), (mob_b, mob_a)])
                    self._host_broadcast(
                        f"Too close to call — it came down to luck. {winner.leader.name}'s mob wins!"
                    )

        self._host_broadcast(f"{winner.target} loses everything.")
        points_value = self._split_points(winner)

        # Reactions — target responds, then winning mob members
        target = self._agent_by_name(winner.target)
        if target:
            self.turn_manager._basic_turn(target, "You've been mobbed. React.", "Your reaction.", optional=False)
        self.turn_manager._basic_turn(winner.leader, "Your mob won. React.", "Your reaction.", optional=False)
        return points_value

    
    def _reconsider(self, get_a_point=False):
        announcement = f"Followers - you now have a chance to reconsider. You may switch mobs, or remain where you are."
        if get_a_point:
            announcement += f" If you choose to switch, you will earn {self.points_string(self.RECONSIDER_POINTS)}."
        self._host_broadcast(announcement)

        followers = [f for mob in self.mobs for f in mob.followers]
        if self.PARALLEL_CHANGING: 
            self._run_tasks(
                [(follower,) for follower in followers],
                lambda follower: self._change_sides(follower, get_a_point=get_a_point)
            )
        else:
            for follower in followers:
                self._change_sides(follower, get_a_point=get_a_point)
        

    def _change_sides(self, player, get_a_point=False):
        current_mob = next((m for m in self.mobs if player in m.followers), None)
        other_mobs = [m for m in self.mobs if m is not current_mob]
        choices = [self._mob_label(m) for m in other_mobs] + [self.STAY]
        action_fields = self.turn_manager.create_choice_field(
            "mob_choice", choices, "Choose a mob to switch to, or 'Stay' to remain where you are."
        )
        nudge = (
            f"You will earn {self.points_string(self.RECONSIDER_POINTS)} if you switch — but consider whether the loyalty cost is worth it."
            if get_a_point else
            "Stay silent and leave this blank unless you are switching. Silence means you stay."
        )
        model = DynamicModelFactory.create_model_(
            player,
            action_fields=action_fields, #maybe we do need to add optional here
            public_response_prompt="If you are switching, say something as you cross the floor. Otherwise leave this null.",
            additional_thought_nudge=nudge
        )
        result = player.take_turn_standard(
            f"The mobs as they stand:\n{self._mobs_string(self.mobs)}\nYou are currently in {self._mob_label(current_mob)}. Will you stay or switch?",
            self.gameBoard, model
        )
        choice = result.mob_choice.strip()
        chosen_mob = next((m for m in other_mobs if self._mob_label(m) == choice), None)
        if choice == self.STAY or not chosen_mob:
            if choice not in (self.STAY, "") and not chosen_mob:
                self.private_system_message(player, f"Invalid choice '{choice}' — you remain in {self._mob_label(current_mob)}.")
            self._host_broadcast(f"{player.name} stays.")
            return
        current_mob.followers.remove(player)
        chosen_mob.followers.append(player)
        if get_a_point:
            self.gameBoard.append_agent_points(player.name, self.RECONSIDER_POINTS)
        self.gameBoard.handle_public_private_output(player, result)
        self._host_broadcast(f"{player.name} switches to {self._mob_label(chosen_mob)}!")
        
        
    def run_game(self):
        self.mobs: list[Mob] = []
        agents = self._shuffled_agents()
        host_intro = ("Welcome to Mob Mentality- the game where you will be a Mob Boss- or a Henchmen. "
        "Mob rules- only the biggest mob will get their target...and share their points. "
        "We will start with a choice: will you pick a target and lead the mob? "
        "Or wait to see where the wind is blowing, and join the mob? ")
        self._host_broadcast(host_intro)

        for agent in agents:
            mob = self._decide_to_be_leader(agent, agents)
            self._react_to_mob_initiation(agent, mob)
            if mob:
                self.mobs.append(mob)

        if not self.mobs:
            self._force_mob_leaders()

        if len(self.mobs) == 1:
            self._host_broadcast(f"Only one person was brave enough to step forward — {self.mobs[0].leader.name} will reap the rewards.")
            self._split_points(self.mobs[0])
            return

        self._announce_mobs_initial()
        leaders = [mob.leader for mob in self.mobs]
        followers = [agent for agent in agents if agent not in leaders]
        if followers:
            self._host_broadcast(f"Now our undeclared players must make a decision. {self.format_list([a.name for a in followers])}.")

        self._choose_to_join_mobs(followers)

        self._consolidate_mobs()

        while len(self.mobs) > 2:
            self._announce_mobs()
            smallest = min(self.mobs, key=lambda m: len(m.followers) + 1)
            self._disband_mob(smallest)
            self._reconsider(get_a_point=True)

        self._finale()

      