import random
from gameplay_management.base_manager import BaseRound
from models.player_models import DynamicModelFactory
from prompts.gamePrompts import GamePromptLibrary


class GameMob(BaseRound):

    @classmethod
    def display_name(cls, cfg):
        return "The Mob"

    @classmethod
    def rules_description(cls, cfg):
        return (
            "Players can nominate themselves as mob leaders and announce a target. "
            "All other players secretly pledge to a mob. Smaller mobs are disbanded and members choose again. "
            "This repeats until two mobs remain. The larger mob wins — the target loses ALL their points, "
            "split among the winning mob members. In a tie, each target loses half."
        )

    @classmethod
    def is_game(cls):
        return True

    def run_game(self):
        # ── 1. Leader nomination (optional) ── players can step up as mob leader
        # pseudo: each player gets optional turn to nominate themselves
        # pseudo: if they nominate, they must announce their target
        # pseudo: leaders = [{leader: agent, target: agent}, ...]

        # ── 2. Target reactions ── targeted players respond publicly
        # pseudo: targets plead, threaten, or rally counter-mobs

        # ── 3. Secret pledging ── non-leaders secretly pick a mob (parallel)
        # pseudo: choice field with leader names
        # pseudo: all revealed simultaneously

        # ── 4. Disband smallest mobs ── members of smallest mob(s) choose again
        # pseudo: repeat until exactly 2 mobs remain
        # pseudo: disbanded members get new choice between remaining mobs

        # ── 5. Resolve ── bigger mob wins
        # pseudo: if tied — each target loses half points, split among respective mobs
        # pseudo: if clear winner — target loses ALL points, split among winning mob
        # pseudo: losing mob gets nothing

        # ── 6. Reactions ── target and winners respond
        pass
