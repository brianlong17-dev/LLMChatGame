from collections import Counter
from typing import List, Optional, Sequence
from gameplay_management.base_manager import *
from prompts.gamePrompts import GamePromptLibrary
from prompts.prompts import PromptLibrary
from prompts.votePrompts import VotePromptLibrary
    
   
class VoteMechanicsMixin(BaseRound):
    def __init__(self, gameBoard, simulationEngine):
        super().__init__(gameBoard, simulationEngine) 
    
    ###############
    #   Helper    #
    ###############
    
    @classmethod
    def is_vote(cls):
        return True
    
        
    def eliminate_player_by_name(self, player_name):
        victim = next((a for a in self.simulationEngine.agents if a.name == player_name), None)
        if victim:
            victim.game_over = True
            host_message = VotePromptLibrary.elimination_host_msg.format(victim_name=victim.name)
            self.gameBoard.host_broadcast(host_message)
            final_words_prompt = PromptLibrary.final_words_prompt()

            
            self.simulationEngine.eliminate_player(victim)
            self.gameBoard.remove_agent_state(victim.name)
            final_words_result = self.respond_to(victim, final_words_prompt)

            self.publicPrivateResponse(victim, final_words_result)
        else:
            print(f"NOT FOUND: {player_name}")
    
    
    
    def _validate_immunity(self, immunity_players: Optional[Sequence[str]]) -> list[str]:
        
        if immunity_players is None:
            return []
        immunity_players = list(dict.fromkeys(immunity_players))
        if len(self.simulationEngine.agents) == len(immunity_players):
            host_message = VotePromptLibrary.immunity_all_players_reset
            self.gameBoard.host_broadcast(host_message)
            immunity_players = []
        return immunity_players
       
   
    
    def immunity_string(self, immunity_players: Sequence[str], players_up_for_elimination: Sequence[str]) -> str:
        immunity_string = ""
        if immunity_players:
            immunity_string = (
                f"{VotePromptLibrary.immunity_players_prefix}\n"
                f" {', '.join(immunity_players)}.\n"
            )
        players_up_for_elimination_string = (
            f"\n{VotePromptLibrary.elimination_players_prefix}\n"
            f" {', '.join(players_up_for_elimination)}\n"
        )
        return f"{immunity_string}{players_up_for_elimination_string}\n"
            

    def _players_up_for_elimination(self, immunity_players: Optional[Sequence[str]]) -> List['Debater']:
        immunity_players = immunity_players or []
        return  [a for a in self.simulationEngine.agents if a.name not in immunity_players]
        
    ###############
    #   Logic     #
    ###############
    def vote_one_player_off(self, player, eligible_players_names):
        names_str = self.format_list(eligible_players_names)
        user_content = VotePromptLibrary.vote_one_player_user_content.format(
            eligible_player_names=names_str
        )
        name_field_prompt = VotePromptLibrary.vote_one_player_name_field_prompt
        #----------------
        action_fields = self._choose_name_field(eligible_players_names, name_field_prompt) 
        response_model = DynamicModelFactory.create_model_(player, model_name="vote_out_player", action_fields=action_fields) 
        vote_result = player.take_turn_standard(user_content, self.gameBoard, response_model)
        #-----------------
        return vote_result
           
    def _collect_votes(self, players_up_for_elimination: Sequence[str], pass_allowed: bool = False):
        votes = []
        voting_results = []
        voting_futures = []
        with ThreadPoolExecutor() as executor:
            for agent in self.simulationEngine.agents:
                future = executor.submit(self.vote_one_player_off, agent, players_up_for_elimination)
                voting_futures.append(future)

            voting_results = [vote_future.result() for vote_future in voting_futures]

        for agent, vote_response in zip(self.simulationEngine.agents, voting_results):
            actual_vote = getattr(vote_response, GamePromptLibrary.model_field_choose_name, None)
            actual_vote = actual_vote.strip() if actual_vote else ""
            
            if actual_vote not in players_up_for_elimination:
                if pass_allowed:
                    print(
                        VotePromptLibrary.collect_votes_invalid_skip_msg.format(
                            agent_name=agent.name, vote=actual_vote
                        )
                    )
                    actual_vote = None
                else:
                    print(
                        VotePromptLibrary.collect_votes_invalid_self_msg.format(
                            agent_name=agent.name, vote=actual_vote
                        )
                    )
                if actual_vote:
                    actual_vote = agent.name
            if actual_vote:
                votes.append(actual_vote)
            self.publicPrivateResponse(agent, vote_response)
        return votes, voting_results
   
    def process_vote_rounds(self, players_up_for_elimination: Sequence[str], revote_count: int = 0, initial_votes = None):
        
        if revote_count > 3:
            self.gameBoard.host_broadcast(VotePromptLibrary.voting_round_random_elimination_msg)
            return random.choice(players_up_for_elimination), initial_votes
            #easy to replace this later, with better choice...
        
        
        votes, voting_results = self._collect_votes(players_up_for_elimination)
        voting_results = initial_votes if initial_votes is not None else voting_results
        vote_counts = Counter(votes)
        tally_str = ", ".join([f"{name}: {count} votes" for name, count in vote_counts.items()])
        host_message = VotePromptLibrary.voting_tally_msg.format(tally=tally_str)
        self.gameBoard.host_broadcast(host_message)

        if not vote_counts:
            self.gameBoard.host_broadcast(VotePromptLibrary.voting_round_no_valid_votes_msg)
            return random.choice(players_up_for_elimination), voting_results
        
        # Process results
        max_votes = max(vote_counts.values())
        players_with_most_votes = [name for name, count in vote_counts.items() if count == max_votes]
        
        if len(players_with_most_votes) > 1:
            deadlock_string = VotePromptLibrary.voting_round_tie_msg.format(
                players_with_most_votes=self.format_list(players_with_most_votes)
            )
            if len(players_with_most_votes) == len(self.simulationEngine.agents):
                deadlock_string = VotePromptLibrary.voting_round_complete_deadlock_msg.format(
                    max_votes=max_votes
                )
            self.gameBoard.host_broadcast(deadlock_string)
            return self.process_vote_rounds(players_with_most_votes, (revote_count + 1), voting_results)
        else:
            return players_with_most_votes[0], voting_results
     
       
    def _dispense_victim_points(self, victim_name, voting_results, points_per_survived_vote=None):
        if not points_per_survived_vote:
            points_per_survived_vote = GamePromptLibrary.points_per_survived_vote
        survivors_rewarded = {}
        for vote_obj in voting_results:
            targeted_player = getattr(vote_obj, GamePromptLibrary.model_field_choose_name, None)
            targeted_player = targeted_player.strip() if targeted_player else ""
            if targeted_player and targeted_player != victim_name:
                self.gameBoard.append_agent_points(targeted_player, points_per_survived_vote)
                survivors_rewarded[targeted_player] = survivors_rewarded.get(targeted_player, 0) + points_per_survived_vote

        if survivors_rewarded:
            reward_str = ", ".join([f"{name} (+{pts})" for name, pts in survivors_rewarded.items()])
            
            self.gameBoard.host_broadcast(
                f"🛡️ BULLET DODGER BONUS! The following players took heat but survived the vote. "
                f"They receive points for every vote they survived: {reward_str}"
            )
   
    ###############
    #   Running   #
    ###############        
    
    