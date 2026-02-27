from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from pydantic import Field

from gameplay_management.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory


class GamePerformSobStory(GameMechanicsMixin):

    # ------------------------------------------------------------------
    # Sob Story
    # ------------------------------------------------------------------

    def _get_sob_story(self, player, user_content, response_model):
        response = player.take_turn_standard(user_content, self.gameBoard, response_model)
        return player, response

    def _get_sob_story_judgement(self, judge, user_content, response_model):
        response = judge.take_turn_standard(user_content, self.gameBoard, response_model)
        return judge, response

    def _build_score_summary(self, performer_name: str, scores: dict[str, int]) -> tuple[str, int]:
        """
        Returns (host_summary_string, average_score_rounded).
        scores is {judge_name: score_int}.
        """
        individual = ",  ".join(f"{name}: {score}" for name, score in scores.items())
        average = round(sum(scores.values()) / len(scores)) if scores else 0
        summary = (
            f"🎭 Scores for {performer_name} — {individual}\n"
            f"⭐ Average: {average} points awarded!"
        )
        return summary, average

    def run_game_sob_story(self):
        """
        Phase 1 — All players write their sob story in parallel (using higher model).
        Phase 2 — Stories are performed one by one. After each performance, all other
                   players judge in parallel; judgements are published one by one before
                   moving to the next performer. The performer receives their average score.
        """

        # --- Host intro -------------------------------------------------------
        host_intro = (
            "💔 SOB STORY!\n"
            "Every reality contestant has one — a traumatic past, a hurdle they overcame, "
            "the people left behind. Now is your chance to share your vulnerability.\n"
            "Your fellow contestants will judge your story on a scale of 1-10. "
            "Did it pull at the heartstrings? Was it honest, vulnerable — and do they even like you?"
        )
        self.gameBoard.host_broadcast(host_intro)

        agents = self._shuffled_agents()

        # --- Phase 1: Generate all stories in parallel (higher model) ---------
        story_prompt = (
            "Write your sob story. Pour your heart out — or don't. "
            "Make it heartwarming, heartstring-tugging, honest, vulnerable, "
            "absurd, strategic... whatever you think will move your fellow contestants. "
            "Your public response IS your story."
        )

        story_futures = []
        with ThreadPoolExecutor() as executor:
            for player in agents:
                player.use_higher_model = True
                #we may have to use a different action field here- replace with public response with brief word before you go - 'here goes!'
                response_model = DynamicModelFactory.create_model_(
                    player,
                    model_name="SobStory",
                    public_response_prompt=(
                        "Your sob story. This is your performance — make it count."
                    ),
                    private_thoughts_prompt=(
                        "What are you really going for here? What impression do you want to leave?"
                    ),
                )
                future = executor.submit(self._get_sob_story, player, story_prompt, response_model)
                story_futures.append(future)

        stories = [f.result() for f in story_futures]  # list of (player, response)

        # --- Phase 2: Perform and judge one by one ----------------------------
        score_choices = [str(i) for i in range(1, 11)]
        round_scores: dict[str, int] = {}

        for performer, story_response in stories:

            # Announce performer and publish their story
            self.gameBoard.host_broadcast(
                f"🎤 {performer.name} takes the stage..."
            )
            self.publicPrivateResponse(performer, story_response, delay=1)

            # Build judging context — other players only
            other_players = [a for a in agents if a is not performer]
            story_text = story_response.public_response

            judging_prompt = (
                f"{performer.name} just shared their sob story:\n\n"
                f"\"{story_text}\"\n\n"
                f"Give your honest (or strategic) score and critique. "
                f"Your public response is your spoken critique — everyone will hear it."
            )

            action_fields = self.create_choice_field(
                "score",
                score_choices,
                f"Your score for {performer.name}'s story. 1 = unmoved, 10 = devastated.",
            )

            game_logic_fields = {
                "judging_criteria": (
                    str,
                    Field(
                        description=(
                            "What lens are you judging through? Emotional authenticity? Language? Is it beautifully expressed?"
                            "Delivery? Strategic value to you? How you feel about this player personally?"
                        )
                    ),
                ),
                "strategic_calculation": (
                    str,
                    Field(
                        description=(
                            "Is there a game reason to score high or low? "
                            "Can you low-ball without blowback — remember, they'll be judging you too. "
                            "Consistently low scores will be remembered and returned. "
                            "Genuinely consider giving a 10 if it's great."
                        )
                    ),
                ),
            }

            # Collect all judgements in parallel
            judge_futures = []
            with ThreadPoolExecutor() as executor:
                for judge in other_players:
                    response_model = DynamicModelFactory.create_model_(
                        judge,
                        model_name="SobStoryJudge",
                        game_logic_fields=game_logic_fields,
                        action_fields=action_fields,
                        public_response_prompt=(
                            f"Your spoken critique of {performer.name}'s story. "
                            "Be honest, be cutting, be generous — your call."
                        ),
                        private_thoughts_prompt=(
                            "What do you secretly think? What's really behind your score?"
                        ),
                    )
                    future = executor.submit(
                        self._get_sob_story_judgement, judge, judging_prompt, response_model
                    )
                    judge_futures.append(future)

            judgements = [f.result() for f in judge_futures]  # list of (judge, response)

            # Publish judgements one by one and collect scores
            scores = {}
            for judge, judgement in judgements:
                self.publicPrivateResponse(judge, judgement, delay=1)
                raw_score = getattr(judgement, "score", None)
                try:
                    scores[judge.name] = int(raw_score)
                except (TypeError, ValueError):
                    scores[judge.name] = 5  # fallback if model misbehaves

            # Host reads the score summary and awards points
            summary, average = self._build_score_summary(performer.name, scores)
            self.gameBoard.host_broadcast(summary)
            self.gameBoard.append_agent_points(performer.name, average)
            round_scores[performer.name] = average
            performer_score_response = self.respond_to(performer, summary)
            self.publicPrivateResponse(performer, performer_score_response)
        
        # --- Final scoreboard -------------------------------------------------
        round_summary_str = ",  ".join(
            f"{name}: {score}" for name, score in round_scores.items()
        )
        overall_str = ",  ".join(
            f"{name}: {score}" for name, score in self.gameBoard.agent_scores.items()
        )
        self.gameBoard.host_broadcast(
            f"🎭 SOB STORY results — {round_summary_str}\n"
            f"🏆 Overall standings — {overall_str}\n"
        )