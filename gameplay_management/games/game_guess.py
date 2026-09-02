from concurrent.futures import ThreadPoolExecutor
import random
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from gameplay_management.human_turn_form import HumanInputDescription



class GameGuess(GameMechanicsMixin):
    @classmethod
    def display_name(cls, cfg):
        return "Guess"

    @classmethod
    def rules_description(cls, cfg):
        return f"Guess the correct number (1-{cfg.guess_number_range}) to win!"
    
    def run_game(self):
        self.run_game_guess_the_number()
    
    def run_game_guess_the_number(self):
        number_range = self.cfg.guess_number_range
        winning_number = self._pick_winning_number(number_range)
        points_for_correct = number_range

        self._initialise_widget(self.simulationEngine.agents, number_range)
        self._run_intro(number_range, points_for_correct)

        action_fields = self._guess_action_field(number_range)
        player_prompt = self._guess_prompt(number_range, points_for_correct)

        results = self._collect_guesses(player_prompt, action_fields)
        correct, incorrect = self._publish_guesses(results, winning_number)
        result_string = self._award_and_announce(correct, incorrect, winning_number, points_for_correct)
        self._run_reactions(correct, incorrect, result_string)


    # ------------------------------------------------------------------
    # Game helper methods
    # ------------------------------------------------------------------
    
    def _run_intro(self, number_range, points_for_correct):
        host_intro = (
            f"GUESS THE NUMBER!\n"
            f"I'm thinking of a number between 1 and {number_range}.\n"
            f"Guess correctly and you'll win {points_for_correct} points!"
        )
        self.game_board.host_broadcast(host_intro)
    
    def _pick_winning_number(self, number_range):
        return random.randint(1, number_range)

    def _human_guess_description(self):
        return HumanInputDescription(
            titles={"choice": "What's your guess?"},
            placeholders={"public_response": "(optional) anything to add?"},
            underlines=["everyone guesses at the same time"],
        )

    def _human_reaction_description(self, is_correct):
        if is_correct:
            return HumanInputDescription(
                titles={"public_response": "You got it! What do you say?"},
                placeholders={"public_response": "yay!"},
            )
        return HumanInputDescription(
            titles={"public_response": "Only you missed. What do you say?"},
            placeholders={"public_response": "..."},
        )

    def _get_number_guess(self, player, turn_prompt, action_fields):
        #if human guess description is build
        response = self.turn_manager.take_turn(player, turn_prompt, action_fields = action_fields,
            human_input_description_object=self._human_guess_description())
        self._widget_update_entry(player.name, state="picked")
        return player, response

    

    def _build_guess_the_number_result_string(self, correct, incorrect, number_range):
        parts = []

        if correct:
            names = self.format_list([p.name for p in correct])
            parts.append(f"CORRECT! {names} each earn *{number_range} points*!\n\n")

        if incorrect:
            names = self.format_list([p.name for p in incorrect])
            parts.append(f"FLOP! {names} missed the mark.\n\n")

        return "  ".join(parts) if parts else "No valid guesses this round."

    
        
    
    
    def _guess_action_field(self, number_range):
        return self.turn_manager.create_choice_field(
            "choice",
            [str(i) for i in list(range(1, number_range + 1))],
            f"Which number do you guess? Choose between 1 and {number_range}.",
        )
        
    def _guess_prompt(self, number_range, points_for_correct):
        return (
            f"Guess a number between 1 and {number_range}. "
            f"A correct guess wins you {points_for_correct} points. "
            f"What number feels right?"
        )

    def _collect_guesses(self, player_prompt, action_fields):
        futures = []
        with ThreadPoolExecutor() as executor:
            for agent in self.simulationEngine.agents:
                future = executor.submit(
                    self._get_number_guess, agent, player_prompt, action_fields
                )
                futures.append(future)
        return [f.result() for f in futures]

    def _publish_guesses(self, results, winning_number):
        correct = []
        incorrect = []

        for player, response in results:
            raw_choice = getattr(response, "choice", None)
            guess = int(raw_choice)
            widget = self._build_widget_update_entry(player.name, state="revealed", guess=guess)
            self.turn_manager._output_response(player, response, pre_message_choice_reveal="choice", delay=1, is_reply=True,
                                               widget=widget)

            if guess == winning_number:
                correct.append(player)
            else:
                incorrect.append(player)

        return correct, incorrect

    def _award_and_announce(self, correct, incorrect, winning_number, points_for_correct):
        self.game_board.host_broadcast(
            f"The correct number was... **{winning_number}**!"
        )

        result_string = self._build_guess_the_number_result_string(
            correct, incorrect, points_for_correct
        )

        results_widget = None
        for player in correct:
            results_widget = self._build_widget_update_entry(player.name, correct=True, points=points_for_correct) or results_widget
        for player in incorrect:
            results_widget = self._build_widget_update_entry(player.name, correct=False) or results_widget

        self.game_board.host_broadcast(result_string, widget=results_widget)

        for player in correct:
            self.game_board.append_agent_points(player.name, points_for_correct)

        return result_string

    def _run_reactions(self, correct, incorrect, result_string):
        agents_for_response = []
        if len(correct) == 1:
            agents_for_response.append((correct[0], True))
        if len(incorrect) == 1:
            agents_for_response.append((incorrect[0], False))
        if not agents_for_response:
            return

        reaction_futures = []
        with ThreadPoolExecutor() as executor:
            for player, is_correct in agents_for_response:
                future = executor.submit(self.turn_manager.respond_to, player, result_string, broadcast=False,
                    human_input_description_object=self._human_reaction_description(is_correct))
                reaction_futures.append((player, future))

        for player, future in reaction_futures:
            reaction = future.result()
            self.turn_manager._output_response(player, reaction, delay=0.1, is_reply=True)
            
            
    # ---
    # widget helpers
    # ---
    def _build_widget_update_entry(self, name, state=None, guess=None, correct=None, points=None):
        for entry in self._widget_rows:
            if entry["name"] == name:
                if state:
                    entry["state"] = state
                if guess is not None:
                    entry["guess"] = guess
                if correct is not None:
                    entry["correct"] = correct
                if points is not None:
                    entry["points"] = points
                return self._widget_payload()
        return None

    def _widget_update_entry(self, name, state=None, guess=None, correct=None, points=None):
        payload = self._build_widget_update_entry(name, state, guess, correct, points)
        if payload is not None:
            self.game_board.game_sink.on_widget_update(payload)
        return

    def _widget_payload(self):
        return {
            "kind": "guess",
            "range": self._widget_range,
            "rows": self._widget_rows,
        }

    def _emit_widget(self):
        self.game_board.game_sink.on_widget_update(self._widget_payload())

    def _initialise_widget(self, agents, number_range):
        self._widget_range = {"min": 1, "max": number_range}
        self._widget_rows = [
            {"name": agent.name, "state": "waiting", "guess": None, "correct": None, "points": None}
            for agent in agents
        ]
        self._emit_widget()

