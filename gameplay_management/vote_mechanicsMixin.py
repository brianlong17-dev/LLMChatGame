from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Sequence
from gameplay_management.base_manager import *
from prompts.gamePrompts import GamePromptLibrary
from prompts.votePrompts import VotePromptLibrary
    
   
class VoteMechanicsMixin(BaseManager):
    def __init__(self, gameBoard, simulationEngine):
        super().__init__(gameBoard, simulationEngine) 
    
    ###############
    #   Helper    #
    ###############
    def _validate_immunity(self, immunity_players: Optional[Sequence[str]]) -> list[str]:
        if immunity_players is None:
            return []
        invalid_types = [type(player).__name__ for player in immunity_players if not isinstance(player, str)]
        if invalid_types:
            raise TypeError(f"immunity_players must be list[str], got invalid item types: {invalid_types}")
        immunity_players = list(dict.fromkeys(immunity_players))
        if len(self.simulationEngine.agents) == len(immunity_players):
            host_message = VotePromptLibrary.immunity_all_players_reset
            self.gameBoard.host_broadcast(host_message)
            immunity_players = []
        return immunity_players
       
    def eliminate_player_by_name(self, player_name):
        victim = next((a for a in self.simulationEngine.agents if a.name == player_name), None)
        if victim:
            host_message = VotePromptLibrary.elimination_host_msg.format(victim_name=victim.name)
            self.gameBoard.host_broadcast(host_message)
            instruction_override = PromptLibrary.final_words_prompt(self.gameBoard)     
            
            
            self.gameBoard.remove_agent_state(victim.name)
            self.simulationEngine.agents.remove(victim)
            finalWordsResult = self.respond_to(victim, host_message, 
                                               instruction_override = instruction_override)
            print(finalWordsResult)
            self.publicPrivateResponse(victim, finalWordsResult)
            if self.gameBoard.execution_style:
                executionString = self.get_execution_string(victim)
                self.gameBoard.system_broadcast(executionString)
        else:
            print(f"NOT FOUND: " + player_name)
    
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
        return f"{immunity_string}{players_up_for_elimination_string}"
            
    def get_execution_string(self, victim):
        name = victim.name
        string1 = f"{name} is brought onto the podium under the stormy sky. Lightning strikes {name} several times. The pile of ashes is promptly blown away"
        string2 = f"{name} is brought to the edge of a cliff. After some light shoving they loose their footing, falling the 751ft drop the the ocean below."
        string3 = f"{name} is brought to the large pool, where they are pushed in a promptly devoured by piranhas"
        string4 = f"{name} is brought to observe the sausage making machine, where they loose their footing and fall in. The winner will get a chance to have sausages."
        string5 = f"{name} is brought to guillotine and loses their head. As a reportedly lifelong francophile, perhaps it's what they would have wanted."
        strings = [string1, string2, string3, string4, string5]
        return random.choice(strings)

    def _players_up_for_elimination(self, immunity_players: Optional[Sequence[str]]) -> List['Debater']:
        immunity_players = immunity_players or []
        return  [a for a in self.simulationEngine.agents if a.name not in immunity_players]
        
    ###############
    #   Logic     #
    ###############
    def voteOnePlayerOff(self, player, eligible_players_names):
        names_str = ", ".join(eligible_players_names)
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
        votingResults = []
        voting_futures = []
        with ThreadPoolExecutor() as executor:
            for agent in self.simulationEngine.agents:
                # Start the task and store the future object
                future = executor.submit(self.voteOnePlayerOff, agent, players_up_for_elimination)
                voting_futures.append(future)
            
            # 3. Collect results (this waits for everyone to finish)
            votingResults = [vote_future.result() for vote_future in voting_futures]
                
        for agent, vote_response in zip(self.simulationEngine.agents, votingResults):
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
        return votes, votingResults
   
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
                players_with_most_votes=", ".join(players_with_most_votes)
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
        #Was going to give out vitim points, but maybe 1 per vote
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
    def run_voting_winner_chooses(self, immunity_players: Optional[Sequence[str]] = None, with_pass_option: bool = False):
        immunity_players = self._validate_immunity(immunity_players)
            
        leading_player= self.get_strategic_players(self.simulationEngine.agents, top_player = True)[0]
        other_agent_names = [name for name in self.gameBoard.agent_names if name != leading_player.name]
        leading_player_message = VotePromptLibrary.winner_chooses_host_msg.format(
            leading_player_name=leading_player.name,
            other_agent_names=", ".join(other_agent_names),
        )
        self.gameBoard.host_broadcast(leading_player_message)
        context_msg = VotePromptLibrary.winner_chooses_context_msg
        choice_prompt = VotePromptLibrary.winner_chooses_choice_prompt
        additional_thought_nudge = VotePromptLibrary.winner_chooses_thought_nudge
        #--------------
        
        action_fields = self.create_choice_field("target_name", other_agent_names, field_description= choice_prompt)
        model = DynamicModelFactory.create_model_(leading_player, "leader_vote_player_off", 
                    additional_thought_nudge=additional_thought_nudge, action_fields=action_fields)
        response = leading_player.take_turn_standard(context_msg, self.gameBoard, model)
        #-------------
        
        self.publicPrivateResponse(leading_player, response)
        self.eliminate_player_by_name(response.target_name)
    
    def run_voting_round_basic_dont_miss(self, immunity_players: Optional[Sequence[str]], dont_miss: bool = True):
        self.run_voting_round_basic(immunity_players, dont_miss = True)
    
   
    def get_bottom_players(self, players_up_for_elimination, min = 2, multiple = False):
        selected_players = []
        pool = list(players_up_for_elimination)
        while len(selected_players) < min and pool:
            #remaining = count - len(selected_players)
            batch = self.get_strategic_players(pool, top_player = False, multiple = multiple)
            if not batch:
                break
            selected_players.extend(batch)
            pool = [p for p in pool if p not in selected_players]
        return selected_players
    
    def run_voting_bottom_two_only_two(self, immunity_players: Optional[Sequence[str]] = None, multiple: bool = False):
        return self.run_voting_bottom_players(immunity_players, multiple = False, count = 2)
    
    def run_voting_bottom_two_multiple(self, immunity_players: Optional[Sequence[str]] = None, multiple: bool = True):
        return self.run_voting_bottom_players(immunity_players, multiple = True, count = 2)
    
    
    def run_voting_bottom_players(self, immunity_players: Optional[Sequence[str]] = None, dont_miss: bool = True, multiple: bool = False, count: int = 2):
        immunity_players = self._validate_immunity(immunity_players)
        
        host_intro_msg = (f"In this round, the bottom {count} players face elimination.\n")
        if multiple:
            host_intro_msg += (f"In the case more than {count} players share the bottom scores, than more than {count} players may face elimination.\n")
        if dont_miss:
            host_intro_msg +=  f"Any player who receives votes but isn't eliminated will receive a point per failed vote"#self._dont_miss_string#actually something in the promptLibarary
        
        players_up_for_elimination = self._players_up_for_elimination(immunity_players)
        if len(players_up_for_elimination) < 2:
            print("Not enough players!")
            return
        
        players_up_for_elimination = self.get_bottom_players(players_up_for_elimination, min = 2, multiple=multiple)
        
        host_intro_msg += self.immunity_string(immunity_players, 
                                               self._names(players_up_for_elimination))
        
        self.gameBoard.host_broadcast(host_intro_msg)
        
        victim_name, voting_results = self.process_vote_rounds(self._names(players_up_for_elimination))
        if dont_miss:
            self._dispense_victim_points(victim_name, voting_results)
        self.eliminate_player_by_name(victim_name)
              
    def run_voting_round_basic(self, immunity_players: Optional[Sequence[str]] = None, with_pass_option: bool = False, dont_miss: bool = False):
        
        immunity_players = self._validate_immunity(immunity_players)
        if len(self.simulationEngine.agents) <= 2:
            print("WARNING: Only 2 players. Shoudln't run here")
            #maybe run other vote instead
    
        players_up_for_elimination = [a.name for a in self._players_up_for_elimination(immunity_players)]
        pass_rules = f"You may ONLY vote for an active player currently in the game. If you vote for an eliminated player, or refuse to vote, your vote will automatically count as a vote against YOURSELF."
        host_message = (f"🚨🚨🚨 IT'S TIME TO VOTE. "
                        f"It's time to vote. Each player will vote for one player they want to REMOVE from the game. "
                        f"The player that receives the most votes will leave the game IMMEDIATELY."
                        f"{self.immunity_string(immunity_players, players_up_for_elimination, )}\n"
                        f"\n\n{pass_rules}")
        self.gameBoard.host_broadcast(host_message)
        victim_name, voting_results = self.process_vote_rounds(players_up_for_elimination)
        if dont_miss:
            self._dispense_victim_points(victim_name, voting_results)
        self.eliminate_player_by_name(victim_name)
           
    def run_voting_lowest_points_removed(self, immunity_players: Optional[Sequence[str]] = None, with_pass_option: bool = False):
        #immunity is irrelevant here 
        
        player = self.get_strategic_players(self.simulationEngine.agents, top_player = False)[0]
        self.gameBoard.host_broadcast(f"🚨🚨🚨 The time... has come. "
                                     f"The player with the lowest score, will be removed from the game."
                                     f"In the event of a tie, a player will be chosen at random.\n\n"
                                     f"The player with the lowest score and will therefore, be removed from the competition is... {player.name}")
                                     
       
        self.eliminate_player_by_name(player.name)
   
