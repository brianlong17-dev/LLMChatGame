import random
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary
from collections import defaultdict


class GameKnives(BaseRound):

    @classmethod
    def display_name(cls, cfg):
        return "Knives"

    @classmethod
    def rules_description(cls, cfg):
        return (
            "Every player starts with a knife. The lights go off — each player secretly stabs someone or passes (keeping their knife for later). "
            "The lights come back on: the player with the most knives in their back dies. Ties mean all tied players die. "
            "Dead players' knives are randomly redistributed among survivors. Players who passed accumulate knives for future rounds. "
            "If every remaining player dies simultaneously, they all win and earn bonus points (1 point in round 1, 2 in round 2, etc.). "
            "Last 3 standing earn points."
        )

    @classmethod
    def is_game(cls):
        return True

    def _make_choice(self, player, circle, knives_count):
        circle_names = [a.name for a in circle]
        allowed_choices = circle_names + ["Pass"]

        action_fields = {}
        for i in range(knives_count):
            action_fields |= self.create_choice_field(
                f"knife_{i+1}",
                allowed_choices,
                f"Knife {i+1}: choose a player to stab, or 'Pass' to keep this knife for later."
            )

        model = DynamicModelFactory.create_model_(
            player,
            action_fields=action_fields,
            public_response_prompt=(
                "You can say something or stay silent. The lights are off — no one can see your decision. "
                "You can lie, boast, stay quiet... it's up to you."
            ),
            additional_thought_nudge=(
                "Who is the biggest threat? Should you spread your knives or focus on one target? "
                "Is it worth passing to save knives for later?"
            ),
            optional=False #we need to even look into what this does
        )

        knife_str = f"You have {self._knife_string(knives_count)}."
        other_names = [name for name in circle_names if name != player.name]
        user_content = (
            f"The lights are off. {knife_str} "
            f"For each knife, choose someone to stab or pass to keep it. "
            f"You can stab the same person multiple times. You could stab yourself. "
            f"The other players in the circle are: {self.format_list(other_names)}."
        )

        result = player.take_turn_standard(user_content, self.gameBoard, model)
        self.gameBoard.handle_public_private_output(player, result)

        targets = []
        for i in range(knives_count):
            choice = getattr(result, f"knife_{i+1}").strip()
            if choice != "Pass":
                if choice in circle_names:
                    targets.append(choice)
                else:
                    message = f"Oh no, your taget {choice} was invalid! The knife goes in your own back instead. "
                    self.private_system_message(player, message)
                    # Invalid — stab self (shouldn't happen with Pydantic Literal)
                    # TODO: private message — "Your knife slipped..."
                    targets.append(player.name)
        if not targets:
            print (f"{player.name} ({self._knife_string(knives_count)}) passes.")
        else:
            print(f"{player.name} ({self._knife_string(knives_count)}) stabs {self.format_list(targets)}")

        return player.name, targets
        
    
    def _knife_string(self, count):
        word = "knife" if count == 1 else "knives"
        return  f"{count} {word}"
    
    def _annouce_deaths(self, dead_names, count):
        
        announcement = (f"With {self._knife_string(count)} in their back: "
        f"It is with great sadness we annouce the death of {self.format_list(dead_names)}. ")
        
        self.gameBoard.host_broadcast(announcement)
        
    def _knives_count_string(self, knives):
        grouped_knives = defaultdict(list)
        for name, count in knives.items():
            grouped_knives[count].append(name)
        sorted_counts = sorted(grouped_knives.keys(), reverse=True)

        lines = ["The knives for each player:"]
        for count in sorted_counts:
            formatted_names = self.format_list(grouped_knives[count])
            knife_label = self._knife_string(count)  
            lines.append(f"{knife_label}: {formatted_names}")

        # Join everything together with newlines
        return "\n".join(lines)
        
        
    def run_game(self):
        circle = list(self._shuffled_agents())

        self.gameBoard.host_broadcast(
            "Welcome to KNIVES! You each have one knife. When the lights go out, "
            "you can stab someone... or pass and keep your knife for later. "
            "When the lights come up, the player with the most knives in their back dies. Ties? Both die. "
            "But if you survive a stabbing, you keep those knives in your back as weapons for the next round. "
            "If everyone dies at once — game over. "
            "You receive a point for every round you survive. "
            "Remember — the lights are out. No one knows what you did. Let's go!"
        )

        round_number = 0
        knives = {agent.name: 1 for agent in circle}

        while len(circle) > 1:
            round_number += 1
            stabs = {agent.name: 0 for agent in circle}
            
            self.gameBoard.host_broadcast(self._knives_count_string(knives), delay = 1)
            self.gameBoard.host_broadcast(f"Round {round_number}. Ready? Lights out...!", delay = 1)



            tasks = []
            for player in circle:
                if knives[player.name] > 0:
                    tasks.append((player, circle, knives[player.name]))
            results = self._run_tasks(tasks, self._make_choice)
            for result in results:
                player_name, targets = result
                knives[player_name] -= len(targets)
                for name in targets:
                    stabs[name] += 1
                
            
            # ── Private stab reveal ──
            # TODO: private message mechanism
            for agent in circle:
                count = stabs[agent.name]
                if count == 0:
                    pass  # TODO: private_system_message(agent, "You check your back... no knives.")
                else:
                    pass  # TODO: private_system_message(agent, f"Oh no! You've been stabbed {count} time{'s' if count > 1 else ''}!")

            # ── Lights on: resolve ──
            self.gameBoard.host_broadcast("The lights come back on...")

            max_stabs = max(stabs.values())
            dead_names = [name for name, count in stabs.items() if count == max_stabs]
            unhurt = [name for name, count in stabs.items() if count == 0]
            
            

            # All die simultaneously → everyone wins
            if len(dead_names) == len(circle):
                if max_stabs == 0:
                    self.gameBoard.host_broadcast(f"No stabs in the dark... we continue")
                    continue
                
                survivor_names = self.format_list([a.name for a in circle])
                self.gameBoard.host_broadcast(
                    f"Incredible... {survivor_names} — you all go down together. "
                    f"Each with {self._knife_string(max_stabs)} in their back."
                )
            else:
                self._annouce_deaths(dead_names, max_stabs)
                
            

            # Announce results sorted by stabs descending
            sorted_players = sorted(circle, key=lambda a: stabs[a.name], reverse=True)
            for agent in sorted_players:
                count = stabs[agent.name]
                knife_string = self._knife_string(count)
                if agent.name in dead_names:
                    pass
                elif count > 0:
                    self.gameBoard.host_broadcast(f"{agent.name} — {knife_string} in their back, but survives!", delay = 1)
                else:
                    pass
                    
            self.gameBoard.host_broadcast(f"With no knives in their back: {self.format_list(unhurt)}", delay = 1)
                    
            

            # ── Collect dead players' knives (held + back) before removing ──
            pool = []
            dead_agents = [a for a in circle if a.name in dead_names]
            for dead in dead_agents:
                pool += [dead.name] * (knives[dead.name] + stabs[dead.name])
                knives.pop(dead.name, None)
                
            # ── Survivors gain back-knives, update circle ──
            survivors = [a for a in circle if a.name not in dead_names]
            for agent in survivors:
                knives[agent.name] += stabs[agent.name]
            circle = survivors
            if len(circle) == 1:
                survivor_name = circle[0].name
                self.gameBoard.host_broadcast(f"Our last survivor! {survivor_name} receives a bonus of 5 points! ")
                self.gameBoard.append_agent_points(survivor_name, 5)
                break


            self.gameBoard.host_broadcast(f"Redistributing the {self._knife_string(len(pool))} found at the crime scene.")
            # ── Redistribute dead pool round-robin from least-stabbed survivor up ──
            if pool and circle:
                sorted_survivors = sorted(circle, key=lambda a: stabs[a.name])
                for i, knife in enumerate(pool):
                    recipient = sorted_survivors[i % len(sorted_survivors)]
                    knives[recipient.name] += 1
                    #self.gameBoard.host_broadcast(f"{recipient.name} picks up a knife from {knife}.")
                    
            
            
            

            if not circle:
                break

            # ── Award survival point ──
            self.gameBoard.host_broadcast(f"{self.format_list([agent.name for agent in circle])} each get a point for surviving." )
            for agent in circle:
                self.gameBoard.append_agent_points(agent.name, 1)
