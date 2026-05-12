
from typing import List, Optional, Type
from pydantic import BaseModel

from gameplay_management.base_manager import BaseRound
from gameplay_management.immunities.immunity_mechanicsMixin import ImmunityMechanicsMixin

class PhaseRecipe(BaseModel):
    rounds: List[Type[BaseRound]] = None
    immunity_types: Optional[List[Type[ImmunityMechanicsMixin]]] = None
    config_mutations: List[tuple] = []

    def phase_summary_string(self, cfg):
        round_summary = ''
        for round in self.rounds:
            round_summary += f"{round.display_name(cfg)} - {round.rules_description(cfg)}\n"
        return round_summary

    def phase_progress_string(self, cfg, current_index):
        current_index -= 1
        lines = []
        for i, round in enumerate(self.rounds):
            if i < current_index:
                prefix = "✓"
                suffix = ""
            elif i == current_index:
                prefix = "▶"
                suffix = "  [NOW]"
            else:
                prefix = " "
                suffix = ""

            line = f"  {prefix} {round.display_name(cfg)}{suffix}"
            
            # Inline rules for upcoming/current rounds only
            if i >= current_index:
                rules = round.rules_brief(cfg)
                if rules:
                    line += f"  — {rules}"
            
            lines.append(line)

        return "\n".join(lines)

    def detailed_rules_string(self, cfg, current_index):
        rules = []
        for i, round in enumerate(self.rounds):
            if i > current_index:
                if round.is_game() or round.is_vote():
                    rules.append(f"{round.display_name(cfg)} - {round.rules_description(cfg)}")
        if not rules:
            return ""
        return "\nUPCOMING GAME RULES:\n" + "\n".join(rules) + "\n"

    def phase_intro_string(self, phase_number, num_players, cfg):
        #this should not be here
        phase_description = f"🚨 WELCOME PLAYERS, TO PHASE {phase_number} 🚨. "

        #TODO this is temp

        if num_players == 2:
            phase_description += f"Two players remain. Only one player will remain at the end of this phase. "

        #--------------------

        phase_description += f"In this phase we will have: "

        discussion_rounds = [round for round in self.rounds if round.is_discussion()]
        if len(discussion_rounds) == 1:
            phase_description += "A discussion round. "
        elif len(discussion_rounds) > 1:
            phase_description += "Discussion rounds. "


        if any(round.is_game() for round in self.rounds):
            phase_description += "A Game Round. "

        has_elimination = any(round.is_vote() for round in self.rounds)
        if has_elimination:
            phase_description += "An Elimination. "


        if has_elimination and self.immunity_types:
            immunity_message = f"HOWEVER! This elimination round has the following immunities in play:\n"
            for immunity in self.immunity_types:
                immunity_message += f"- {immunity.display_name(cfg)}: {immunity.rules_description(cfg)}\n"
            phase_description += immunity_message


        return phase_description

