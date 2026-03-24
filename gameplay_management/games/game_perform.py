from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from pydantic import Field

from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class GamePerformSobStory(GameMechanicsMixin):
    
    @classmethod
    def display_name(cls, cfg):
        return "Perform your sob story"

    @classmethod
    def rules_description(cls, cfg):
        return "Each player performs, and is scored by their fellow contestants!"
    
    def run_game(self):
        return self.run_game_sob_story()
    
    
    # ------------------------------------------------------------------
    # Sob Story
    # ------------------------------------------------------------------

    def _get_sob_story(self, player, user_content, response_model):
        response = player.take_turn_standard(user_content, self.gameBoard, response_model)
        return player, response

    def _get_sob_story_judgement(self, judge, user_content, response_model, run_in_parallel):
        response = judge.take_turn_standard(user_content, self.gameBoard, response_model)
        #if not parallel you can print here?f
        if not run_in_parallel:
            self.publicPrivateResponse(judge, response, delay=0)
        return judge, response

    def _build_score_summary(self, performer_name: str, scores: dict[str, int]) -> tuple[str, int]:
        
        individual = ",  ".join(f"{name}: {score}" for name, score in scores.items())
        average = round(sum(scores.values()) / len(scores)) if scores else 0
        summary = (
            f"🎭 Scores for {performer_name} — {individual}\n"
            f"⭐ Average: {average} points awarded!"
        )
        return summary, average
    
    def _get_stories(self, agents, run_in_parallel):
        story_prompt = GamePromptLibrary.sob_story_prompt
        story_tasks = []
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
                )
            )
            story_tasks.append((player, story_prompt, response_model))

        stories = self._run_tasks(
                story_tasks,
                self._get_sob_story,
                parallel=run_in_parallel,
            )  # list of (player, response)
        return stories
    
    def _get_judgement_model(self, player_judging, performer):
        score_choices = [str(i) for i in range(1, 11)]
        

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
        return DynamicModelFactory.create_model_(
                        player_judging,
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
        
        
    def _get_judgements(self, performer, other_players, story_text, run_in_parallel):
        

        # Collect all judgements in parallel
        judge_tasks = []
        for judge in other_players:
            judging_prompt = (
                f"{performer.name} just shared their sob story:\n\n"
                f"\"{story_text}\"\n\n"
                f"Give your honest (or strategic) score and critique. "
                f"Your public response is your spoken critique — everyone will hear it."
            )
            response_model = self._get_judgement_model(judge, performer)
            judge_tasks.append((judge, judging_prompt, response_model, run_in_parallel))

        judgements = self._run_tasks(
            judge_tasks,
            self._get_sob_story_judgement,
            parallel=run_in_parallel,
        )  # list of (judge, response)
        return judgements

    def _broadcast_story(self, performer, story_response, delay=1):
        # Announce performer and publish their story
        self.gameBoard.host_broadcast(
            f"🎤 {performer.name} takes the stage..."
        )
        self.publicPrivateResponse(performer, story_response, delay)
            
    def run_game_sob_story(self):
        # --- Host intro -------------------------------------------------------
        host_intro = GamePromptLibrary.sob_story_host_intro
        self.gameBoard.host_broadcast(host_intro)
        agents = self._shuffled_agents()
        run_in_parallel = True

        # --- Phase 1: Generate all stories in parallel (higher model) ---------
        stories = self._get_stories(agents, True)  # Because it's nested anyway, there is no point in running out of P

        # --- Phase 2: Perform and judge one by one ----------------------------
        
        round_scores: dict[str, int] = {}

        for performer, story_response in stories:
            # In sequential mode, stories were already announced during collection.
            self._broadcast_story(performer, story_response)

            # Build judging context — other players only
            other_players = [a for a in agents if a is not performer]
            story_text = story_response.public_response
            judgements = self._get_judgements(performer, other_players, story_text, run_in_parallel)

            # Publish judgements one by one and collect scores
            scores = {}
            for judge, judgement in judgements:
                if run_in_parallel:
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
