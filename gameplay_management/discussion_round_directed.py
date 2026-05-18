from gameplay_management.base_manager import BaseRound


class DiscussionRoundDirected(BaseRound):

    @classmethod
    def display_name(cls, cfg):
        return "Discussion Round"

    @classmethod
    def rules_description(cls, cfg):
        return cfg.discussion_round_topic

    def run_game(self):
        ordered_agents = self._shuffled_agents()
        group_allowed = self.cfg.directed_discussion_group_allowed

        while ordered_agents:
            player = ordered_agents.pop(0)

            names = [agent.name for agent in self.agents if agent != player]

            turn_prompt = "You can directly address another player and get a response. "
            if group_allowed:
                names.append("Group")
                turn_prompt += "Choose Group if you want to address the group. Directing questions is often key to building alliances and building strategy."

            public_response_prompt = "Your statement to the group or to the target you've selected. Don't repeat yourself. If you have nothing new to say don't say anything. "
            additional_thought_nudge = "Have you already spoken in this round? What new can you say? You only want to speak if it avoids repetition. "

            response = self.turn_manager._ask_directed_question(player, names, turn_prompt, public_response_prompt, additional_thought_nudge)

            chosen_name = self.turn_manager._get_target_name_from_response(response)
            chosen_agent = self._agent_by_name(chosen_name.strip())

            appendage = ""
            if chosen_agent:
                if chosen_agent in ordered_agents:
                    ordered_agents.remove(chosen_agent)
                    if ordered_agents:
                        ordered_agents.append(chosen_agent)
                    else:
                        appendage = "This is your last turn in the discussion round. Say anything else you want to say. "

                user_prompt = f"{player.name} last message was directed to you. Please respond directly to them. {appendage}"
                self.turn_manager.respond_to(chosen_agent, user_prompt, public_response_prompt="Your public response. ", broadcast=True, is_reply=True)
