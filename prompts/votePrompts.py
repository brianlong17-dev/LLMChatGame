class VotePromptLibrary:
    immunity_all_players_reset = (
        "All players have immunity this round! This means... NO ONE HAS IMMUNITY. You are all again at risk of being voted out."
    )

    immunity_players_prefix = (
        "The following players have immunity, and cannot be voted for to leave in this round of voting:"
    )
    elimination_players_prefix = "The following players are up for elimination:"

    elimination_host_msg = (
        "A JOURNEY COMES TO AN END- THE RESULTS ARE FINAL. "
        "💀 {victim_name} HAS BEEN EJECTED FROM THE ISLAND. 💀 \n"
    )

    winner_chooses_host_msg = (
        "🚨🚨🚨 The time... has come. The player with the highest score, {leading_player_name}, "
        "gets to choose who leaves the game this round. They cannot choose themselves. "
        "They will choose from the following players:\n {other_agent_names}"
    )
    winner_chooses_context_msg = (
        "As the leading player you get to choose the player who will now leave the competition"
    )
    winner_chooses_choice_prompt = "Choose the player you want to remove from the competition"
    winner_chooses_thought_nudge = (
        "Who do you want to send home? In terms of allies, competition, what is your best choice?"
    )

    vote_one_player_user_content = (
        "You must vote for one player you want to leave the competition. "
        "They player with the most votes will leave the game."
        "Who do you vote to leave? Who do you eliminate from {eligible_player_names} and why?"
    )
    vote_one_player_name_field_prompt = "The exact name of the agent to you want to leave the competition.."

    collect_votes_invalid_skip_msg = "Invalid vote by {agent_name}: '{vote}'. Their vote is skipped."
    collect_votes_invalid_self_msg = (
        "Invalid vote by {agent_name} for '{vote}'. This vote will count as a vote against themselves."
    )

    voting_round_random_elimination_msg = (
        "⚡ The tribe is too stubborn. The Judge steps in and eliminates someone at random!"
    )
    voting_tally_msg = "🗳️ VOTING TALLY: {tally}"
    voting_round_tie_msg = (
        "⚖️ We have a tie between {players_with_most_votes}! "
        "We need to revote on these contestants..."
    )
    voting_round_complete_deadlock_msg = (
        "🌀 COMPLETE DEADLOCK. Everyone received {max_votes} vote(s)! You must REVOTE."
    )
    voting_round_no_valid_votes_msg = (
        "No valid votes were cast. The Judge will eliminate someone at random."
    )
