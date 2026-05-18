from collections import Counter, defaultdict
from dataclasses import dataclass, field

from models.player_models import DynamicModelFactory
from gameplay_management.game_cycle.game_cycle import CycleRound


@dataclass
class _PlayerState:
    agent: object
    held: int = 1   # knives currently in hand
    stabs: int = 0  # knives received this round (resets each round)
    notes: list[str] = field(default_factory=list)  # secret notes received

    @property
    def name(self) -> str:
        return self.agent.name


class GameKnives(CycleRound):

    PASS = "Pass"
    SOLE_SURVIVOR_BONUS = 5

    # Behaviour toggles — flip in cfg or subclass for variants.
    CHATTY_STABBING = False
    RUNNER_UP_POINTS = True
    SECRET_NOTES = True
    _debug = False

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

    # ─────────────────────────── helpers ───────────────────────────

    def _knife_string(self, count):
        return f"{count} {'knife' if count == 1 else 'knives'}"

    def _knives_count_string(self, players):
        grouped = defaultdict(list)
        for p in players:
            grouped[p.held].append(p.name)
        sorted_counts = sorted(grouped.keys(), reverse=True)

        lines = ["The knives for each player:"]
        for count in sorted_counts:
            lines.append(f"{'🗡' * count} - {self.format_list(grouped[count])}")

        return "\n".join(lines)

    # ─────────────────────────── per-player turn ───────────────────────────

    def _make_choice(self, state, players, chatty):
        circle_names = [p.name for p in players]
        other_names = [n for n in circle_names if n != state.name]
        allowed_choices = circle_names + [self.PASS]

        action_fields = {}
        for i in range(1, state.held + 1):
            action_fields |= self.turn_manager.create_choice_field(
                f"knife_{i}",
                allowed_choices,
                f"Knife {i}: choose a player to stab, or 'Pass' to keep this knife for later."
            )
        public_response_prompt = (
            "You can say something or stay silent. The lights are off — no one can see your decision. "
            "You can lie, boast, stay quiet... it's up to you. "
            if chatty
            else "This wont be broadcast and can be left empty. "
        )
        if self.SECRET_NOTES:
            public_response_prompt += "You also have the chance to pass a player a secret note. "
            action_fields |= self.turn_manager.create_choice_field(
                "secret_note_target",
                other_names + [self.PASS],
                "If you want to send a secret private note to someone, address it here — pass if you don't want to send a note."
            )
            action_fields |= self.turn_manager.create_basic_field(
                "note_content",
                "Leave null if you chose pass for secret note. Otherwise — the content of your note. "
                "Sign it off explicitly if you want them to know the sender, or else the note is anonymous.",
                optional=True,
            )

        secret_note_additional_thought = (
            " Also — who do you want to send a secret message to? Do you have something to say? Or do you want to pass."
            if self.SECRET_NOTES
            else ""
        )

        model = DynamicModelFactory.create_model_(
            state.agent,
            action_fields=action_fields,
            public_response_prompt = public_response_prompt,
            additional_thought_nudge=(
                "Who is the biggest threat? Should you spread your knives or focus on one target? "
                "Is it worth passing to save knives for later?" + secret_note_additional_thought
            ),
        )

        knife_str = f"You have {self._knife_string(state.held)}."
        user_content = (
            f"The lights are off. {knife_str} "
            f"For each knife, choose someone to stab or pass to keep it. "
            f"You can stab the same person multiple times. You could stab yourself. "
            f"The other players in the circle are: {self.format_list(other_names)}."
        )

        result = state.agent.take_turn_standard(user_content, self.gameBoard, model)
        if chatty:
            self.gameBoard.handle_public_private_output(state.agent, result)

        targets = []
        
        for i in range(1, state.held + 1):
            choice = getattr(result, f"knife_{i}").strip()
            if choice in circle_names:
                targets.append(choice)

        if not targets:
            self.debug_print(f"{state.name} ({self._knife_string(state.held)}) passes.")
        else:
            target_summary = self.format_list([
                f"{name} ×{n}" if n > 1 else name
                for name, n in Counter(targets).items()
            ])
            self.debug_print(f"{state.name} ({self._knife_string(state.held)}) stabs {target_summary}")

        # ── Secret note: deliver straight to the recipient's state ──
        if self.SECRET_NOTES:
            note_target = (getattr(result, "secret_note_target", "") or "").strip()
            if note_target in other_names:
                content = (getattr(result, "note_content", "") or "").strip()
                if self._debug:
                    print(f"NOTE: from {state.name} to {note_target}: {content}" )
                if content:
                    recipient = next(p for p in players if p.name == note_target)
                    recipient.notes.append(content)
                    

        return state.name, targets

    # ─────────────────────────── announcements ───────────────────────────

    def _announce_stabbings(self, players_by_stabs_desc):
        output_string = "The lights come up... \n"
        for p in players_by_stabs_desc:
            if p.stabs > 0:
                output_string += f"{p.name} - {'🔪' * p.stabs}\n"

        self._host_broadcast(output_string, 1)

    def _announce_deaths(self, dead_names, count):

        announcement = (f"With {self._knife_string(count)} in their back: "
        f"It is with great sadness we announce the death of {self.format_list(dead_names)}. ")

        self.gameBoard.host_broadcast(announcement)
        for name in dead_names:
            self.private_system_message(self._agent_by_name(name), f"{name} - you haven't been eliminated from the game! You're only finished up in the minigame. Well done! ", silent = True)

    # ─────────────────────────── post-round flourishes ───────────────────────────

    def _runner_up_bonus(self, players_by_stabs_desc):
        max_stabs = max(p.stabs for p in players_by_stabs_desc)
        survivors = [p for p in players_by_stabs_desc if p.stabs < max_stabs]
        if not survivors:
            return
        count = survivors[0].stabs  # sorted descending, first survivor has highest stab count
        if count == 0:
            return
        runners_up = [p for p in survivors if p.stabs == count]
        self.gameBoard.host_broadcast(
            f"{count} bonus point{'s' if count > 1 else ''} for being the most stabbed survivor"
            f" go to: {self.format_list([p.name for p in runners_up])}",
            delay=1
        )
        for p in runners_up:
            self.gameBoard.append_agent_points(p.name, count)

        for p in runners_up:
            self.turn_manager._basic_turn(p.agent, f"You were stabbed {count} times, but survived. How do you feel? What do you have to say? Do you have any suspects? ",
                             "Speak to the group. Be coy or brash, or whatever your personality prompts you to do.")

    def _optional_pitch(self, players):
        for p in players:
            self.turn_manager._basic_turn(p.agent, "Before we head to the next round, would you like to say something to the group? ",
                        "Speak to the group, or return an empty response to remain silent. ",
                        private_thoughts_prompt="Could you direct the group? Or will you just draw attention? ",
                        optional=True)

    # ─────────────────────────── round mechanics ───────────────────────────

    def _collect_stabs(self, players):
        """Run choices in parallel and mutate held/stabs on each PlayerState."""
        for p in players:
            p.stabs = 0

        tasks = [(p, players, self.CHATTY_STABBING) for p in players if p.held > 0]
        by_name = {p.name: p for p in players}
        for player_name, targets in self._run_tasks(tasks, self._make_choice):
            by_name[player_name].held -= len(targets)
            for target_name in targets:
                by_name[target_name].stabs += 1

    def _reveal_stabs_privately(self, players):
        for p in players:
            if p.stabs == 0:
                self.private_system_message(p.agent, "You check your back... no knives.", silent = True)
            else:
                self.private_system_message(p.agent, f"Oh no! You've been stabbed {p.stabs} time{'s' if p.stabs > 1 else ''}!", silent = True)
            #TODO -- new mechanism -- light react
            
    def _reveal_notes_privately(self, players):
        for p in players:
            if not p.notes:
                continue
            count = len(p.notes)
            plural = "s" if count > 1 else ""
            body = "\n\n".join(
                f"{i}. {note}" for i, note in enumerate(p.notes, start=1)
            )
            self.private_system_message(
                p.agent,
                f"You received {count} secret note{plural}:\n\n{body}",
                silent=False,
            )
            p.notes.clear()
       
    def _redistribute(self, pool_size, survivors):
        """Round-robin the dead's knives starting from the least-stabbed survivor."""
        if not pool_size or not survivors:
            return
        ordered = sorted(survivors, key=lambda p: p.stabs)
        for i in range(pool_size):
            ordered[i % len(ordered)].held += 1

    # ─────────────────────────── main loop ───────────────────────────

    def run_game(self):
        self._cycle_game_setup()
        players = [_PlayerState(agent=a) for a in self._shuffled_agents()]
        for p in players:
            self.private_system_message(p.agent, "This is a parlor game- you can play it up but the knives aren't real- the only backstabbing is strategic. The only thing at stake- points, and your place in the competition.")

        points_string = (
            "The player with most stabbings who survives gets a point for each knife. "
            if self.RUNNER_UP_POINTS
            else "You receive a point for every round you survive. "
        )

        self.gameBoard.host_broadcast(
            "Welcome to KNIVES! You each have one knife. When the lights go out, "
            "you can stab someone... or pass and keep your knife for later. "
            "When the lights come up, the player with the most knives in their back dies. Ties? Both die. "
            "But if you survive a stabbing, you keep those knives in your back as weapons for the next round. "
            "If everyone dies at once — game over. "
            f"{points_string} "
            "Remember — the lights are out. No one knows what you did. Let's go!"
        )
        
        if self.SECRET_NOTES:
            self.gameBoard.host_broadcast("When the lights go out, you also have the opportunity to pass a note to another player- signed or anonymous. ")

        round_number = 0
        while len(players) > 1:
            # Compress at the top of the loop because the round body has multiple exit points (break/continue).
            self._compress_round()
            round_number += 1
            next_players = self._play_round(players, round_number)
            if next_players is None:
                break
            players = next_players

        self._cycle_game_teardown()

    def _play_round(self, players, round_number):
        """Run one round. Returns the surviving players, or None if the game ends."""
        #input("continue? ")  # TEMP: manual step-through
        self.gameBoard.host_broadcast(self._knives_count_string(players), delay = 1)
        if self.optional_responses_in_use:
            self._optional_pitch(players)
        self.gameBoard.host_broadcast(f"Round {round_number}. Ready? Lights out...!", delay = 1)

        self._collect_stabs(players)
        self._reveal_stabs_privately(players)
        self._reveal_notes_privately(players)

        # ── Lights on: resolve ──
        max_stabs = max(p.stabs for p in players)
        dead = [p for p in players if p.stabs == max_stabs]
        survivors = [p for p in players if p.stabs < max_stabs]
        sorted_players = sorted(players, key=lambda p: p.stabs, reverse=True)

        self._announce_stabbings(sorted_players)

        # All die simultaneously → either a quiet round or everyone wins
        if not survivors:
            if max_stabs == 0:
                self.gameBoard.host_broadcast(f"No stabs in the dark... we continue. ")
                #"I think each player should get to say something here lol theyre conspiring. "
                return players

            survivor_names = self.format_list([p.name for p in players])
            self.gameBoard.host_broadcast(
                f"Incredible... {survivor_names} — you all go down together. "
                f"Each with {self._knife_string(max_stabs)} in their back."
            )
            return None

        self._announce_deaths([p.name for p in dead], max_stabs)

        #self._distribute_points()

        if self.RUNNER_UP_POINTS:
            self._runner_up_bonus(sorted_players)
        else:
            # ── Award survival point ──
            self.gameBoard.host_broadcast(f"{self.format_list([p.name for p in survivors])} each get a point for surviving." )
            for p in survivors:
                self.gameBoard.append_agent_points(p.name, 1)

        # ── Pool the dead's knives (held + lodged-in-back) for redistribution ──
        pool_size = sum(p.held + p.stabs for p in dead)

        # ── Sole survivor — bonus and game ends ──
        if len(survivors) == 1:
            sole = survivors[0]
            self.gameBoard.host_broadcast(f"Our last survivor! {sole.name} receives a bonus of {self.SOLE_SURVIVOR_BONUS} points! ")
            self.gameBoard.append_agent_points(sole.name, self.SOLE_SURVIVOR_BONUS)
            return None

        # ── Survivors gain back-knives ──
        self.gameBoard.host_broadcast(f"Redistributing the {self._knife_string(pool_size)} found on {self.format_list([p.name for p in dead])}...\n\n", delay = 1)
        for p in survivors:
            p.held += p.stabs

        self._redistribute(pool_size, survivors)
        return survivors



