from concurrent.futures import ThreadPoolExecutor
from gameplay_management.games.game_mechanicsMixin import GameMechanicsMixin
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class GameRockPaperScissors(GameMechanicsMixin):

    BEATS = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock",
    }

    @classmethod
    def display_name(cls, cfg):
        return "Rock Paper Scissors"

    @classmethod
    def rules_description(cls, cfg):
        cfg_ = cfg
        return (
            f"Players are paired up and simultaneously choose Rock, Paper, or Scissors. "
            f"Win: {cfg_.rps_points_win} pts | Tie: {cfg_.rps_points_tie} pts each | Lose: 0 pts."
        )

    def _points_string(self):
        cfg = self.cfg()
        return (
            f"- WIN  → {cfg.rps_points_win} points\n"
            f"- TIE  → {cfg.rps_points_tie} points each\n"
            f"- LOSE → 0 points\n"
        )

    def _get_rps_choice(self, player, opponent):
        user_content = GamePromptLibrary.rps_game_prompt.format(
            opponent_name=opponent.name,
            points_string=self._points_string(),
        )
        choices = ["rock", "paper", "scissors"]
        action_fields = self.create_choice_field("action", choices)
        additional_thought_nudge = (
            "Think carefully — what would your opponent choose? "
            "Is there a psychological edge you can exploit?"
        )
        model = DynamicModelFactory.create_model_(
            player, "rps_choice",
            additional_thought_nudge=additional_thought_nudge,
            action_fields=action_fields,
        )
        return player.take_turn_standard(user_content, self.gameBoard, model)

    def _calculate_outcome(self, choice0, choice1, name0, name1):
        cfg = self.cfg()
        c0 = choice0.strip().lower().replace(".", "")
        c1 = choice1.strip().lower().replace(".", "")

        EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        e0 = EMOJI.get(c0, c0)
        e1 = EMOJI.get(c1, c1)

        if c0 not in self.BEATS or c1 not in self.BEATS:
            return 0, 0, f"Someone made an invalid move! No points awarded."

        if c0 == c1:
            pts = cfg.rps_points_tie
            msg = f"It's a TIE! Both {name0} and {name1} chose {e0} {c0}. Each gets {pts} points."
            return pts, pts, msg

        if self.BEATS[c0] == c1:
            pts = cfg.rps_points_win
            msg = f"{e0} {c0.upper()} beats {e1} {c1}! {name0} WINS and earns {pts} points!"
            return pts, 0, msg

        pts = cfg.rps_points_win
        msg = f"{e1} {c1.upper()} beats {e0} {c0}! {name1} WINS and earns {pts} points!"
        return 0, pts, msg

    def _execute_pairs(self, pairs):
        for agent0, agent1 in pairs:
            self.gameBoard.host_broadcast(f"{agent0.name} vs {agent1.name} — Rock, Paper, or Scissors?\n")

            with ThreadPoolExecutor() as executor:
                future0 = executor.submit(self._get_rps_choice, agent0, agent1)
                future1 = executor.submit(self._get_rps_choice, agent1, agent0)
                results = [future0.result(), future1.result()]

            choices = []
            for agent, res in zip((agent0, agent1), results):
                self.publicPrivateResponse(agent, res)
                choices.append(res.action.strip().lower())

            p0_gain, p1_gain, msg = self._calculate_outcome(choices[0], choices[1], agent0.name, agent1.name)

            for agent, gain in zip((agent0, agent1), (p0_gain, p1_gain)):
                self.gameBoard.append_agent_points(agent.name, gain)

            self.gameBoard.host_broadcast(f"{msg}\n")

            for agent in (agent0, agent1):
                reaction = self.respond_to(agent, msg)
                self.publicPrivateResponse(agent, reaction)

    def run_game(self):
        self.gameBoard.host_broadcast(GamePromptLibrary.rps_game_intro)

        agents = list(self.simulationEngine.agents)
        pairs, leftover = self._generate_pairings(agents, choose_partner=False)

        if leftover:
            auto_pts = self.cfg().rps_odd_player_auto_points
            self.gameBoard.host_broadcast(
                f"{leftover.name} has no opponent this round — they automatically receive {auto_pts} points.\n\n"
            )
            self.gameBoard.append_agent_points(leftover.name, auto_pts)

        self._execute_pairs(pairs)
