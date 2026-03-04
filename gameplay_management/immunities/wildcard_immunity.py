from gameplay_management.immunity_mechanicsMixin import ImmunityMechanicsMixin


class WildcardImmunity(ImmunityMechanicsMixin):
    def display_name(self):
        return "Wildcard Player Immunity"

    def rules_description(self):
        return (
            "The player deemed to be the most chaotic will receive immunity from the next vote. "
        )

    def run_immunity(self) -> list[str]:
        response = self.gameBoard.game_master.choose_agent_based_on_parameter(
            self.gameBoard,
            self.gameBoard.agent_names,
            "chaotic",
        )
        host_string = (f"The player chosen for the wildcard immunity is... {response.target_name}. "
                       f"The producers say: '{response.public_reason}' \n"
                       f"Well done, {response.target_name}!")
        
        self.gameBoard.host_broadcast(host_string)
        winner = self._agent_by_name(response.target_name)
        winner_response = self.respond_to(winner , host_string)
        self.publicPrivateResponse(winner, winner_response)
        return [response.target_name]
