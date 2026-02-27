from concurrent.futures import ThreadPoolExecutor
import random
from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory



class GameGuess(GameMechanicsMixin):

    # ------------------------------------------------------------------
    # Guess the Number
    # ------------------------------------------------------------------

    def _get_number_guess(self, player, user_content, response_model):
        #why a method?
        response = player.take_turn_standard(user_content, self.gameBoard, response_model)
        return player, response

    def _build_guess_the_number_result_string(self, correct, incorrect, invalid, number_range):
        """Assemble a host broadcast summarising the round."""
        parts = []

        if correct:
            names = ", ".join(p.name for p in correct)
            parts.append(f"🎯 Correct! {names} guessed the number and each earn {number_range} points!")

        if incorrect:
            names = ", ".join(
                f"{p.name} (guessed {g})" for p, g in incorrect
            )
            parts.append(f"❌ Wrong! {names} missed the mark.")

        if invalid:
            names = ", ".join(p.name for p in invalid)
            parts.append(f"⚠️  Invalid guess from: {names}. No points awarded.")

        return "  ".join(parts) if parts else "No valid guesses this round."

    def run_game_guess_the_number(self):
        """
        Each player simultaneously guesses a number between 1 and *number_range*.
        Correct guessers earn *number_range* points.

        number_range is read from game_board.phase_factor.number_range_for_guessing
        with a safe default of 3.
        """
        # --- Config -----------------------------------------------------------
        #number_range = self.gameBoard.phase_factory.number_range_for_guessing
        #TODO  get this from the phaseFactory
        number_range = 4
        winning_number = random.randint(1, number_range)
        points_for_correct = number_range

        # --- Host intro -------------------------------------------------------
        host_intro = (
            f"🔢 GUESS THE NUMBER!\n"
            f"I'm thinking of a number between 1 and {number_range}.\n"
            f"Guess correctly and you'll win {points_for_correct} points!"
        )
        self.gameBoard.host_broadcast(host_intro)

        # --- Build the response model (same for everyone) ---------------------
        valid_choices = list(range(1, number_range + 1))
        action_fields = self.create_choice_field(
            "choice",
            [str(i) for i in valid_choices],
            f"Which number do you guess? Choose between 1 and {number_range}.",
        )
        player_prompt = (
            f"Guess a number between 1 and {number_range}. "
            f"A correct guess wins you {points_for_correct} points. "
            f"Think carefully - what number feels right?"
        )

        
        # --- Collect guesses in parallel (mirrors PD / vote patterns) ---------
        futures = []
        with ThreadPoolExecutor() as executor:
            for agent in self.simulationEngine.agents:
                response_model = DynamicModelFactory.create_model_(
                    agent,
                    model_name="GuessTheNumber",
                    action_fields=action_fields,
                )
                future = executor.submit(
                    self._get_number_guess, agent, player_prompt, response_model
                )
                
                futures.append(future)

        results = [f.result() for f in futures]

        # --- Publish each player's public words & guess -----------------------
        correct = []
        incorrect = []
        invalid = []

        for player, response in results:
            self.publicPrivateResponse(player, response, delay = 1)

            raw_choice = getattr(response, "choice", None)
            try:
                guess = int(raw_choice)
            except (TypeError, ValueError):
                invalid.append(player)
                continue
            
            if guess not in valid_choices:
                invalid.append(player)
            elif guess == winning_number:
                correct.append(player)
            else:
                incorrect.append((player, guess))

        # --- Reveal and award points ------------------------------------------
        self.gameBoard.host_broadcast(
            f"🎲 The number was... **{winning_number}**!"
        )

        result_string = self._build_guess_the_number_result_string(
            correct, incorrect, invalid, points_for_correct
        )
        self.gameBoard.host_broadcast(result_string)

        for player in correct:
            self.gameBoard.append_agent_points(player.name, points_for_correct)

        # --- Reactions (optional but consistent with PD pattern) --------------
        
        reaction_futures = []
        with ThreadPoolExecutor() as executor:
            for player in self.simulationEngine.agents:
                future = executor.submit(self.respond_to, player, result_string)
                reaction_futures.append((player, future))

        
        for player, future in reaction_futures:
            reaction = future.result()
            self.publicPrivateResponse(player, reaction, delay = 1)