from tests.helpers.game_test_helpers import build_pd_game, turn_payload


def test_run_pd_odd_player_gets_auto_split_points():
    game, board, agents, clients = build_pd_game(
        {
            "A1": [
                turn_payload(action="split"),
                turn_payload(public_response="A1 reacts"),
            ],
            "A2": [
                turn_payload(action="split"),
                turn_payload(public_response="A2 reacts"),
            ],
            "A3": [],
        }
    )
    a1, a2, a3 = agents
    game._generate_pairings = lambda _available, _choose_partner, _winner_picks_first: ([(a1, a2)], a3)

    game.run_game_prisoners_dilemma(choose_partner=False)

    assert board.agent_scores["A3"] == 3
    assert board.agent_scores["A1"] == 3
    assert board.agent_scores["A2"] == 3
    clients["A1"].assert_exhausted()
    clients["A2"].assert_exhausted()
    clients["A3"].assert_exhausted()


def test_run_pd_passes_manual_pairing_flags():
    game, _board, agents, _clients = build_pd_game(
        {
            "P1": [turn_payload(action="split"), turn_payload()],
            "P2": [turn_payload(action="steal"), turn_payload()],
        }
    )
    p1, p2 = agents
    seen = {}

    def _generate_pairings(_available, choose_partner, winner_picks_first):
        seen["flags"] = (choose_partner, winner_picks_first)
        return ([(p1, p2)], None)

    game._generate_pairings = _generate_pairings
    game.run_game_prisoners_dilemma(choose_partner=True, winner_picks_first=False)

    assert seen["flags"] == (True, False)


def test_run_pd_collects_decisions_and_reactions_for_each_player():
    game, board, _agents, clients = build_pd_game(
        {
            "Hero": [
                turn_payload(action="split", public_response="hero decision"),
                turn_payload(public_response="Noooo"),
            ],
            "Villain": [
                turn_payload(action="steal", public_response="villain decision"),
                turn_payload(public_response="Worth it"),
            ],
        }
    )

    game.run_game_prisoners_dilemma(choose_partner=False)

    # Each player should have 1 decision + 1 reaction in API calls.
    assert len(clients["Hero"].calls) == 2
    assert len(clients["Villain"].calls) == 2
    host_msgs = [entry["message"] for entry in board.currentRound if entry["speaker"] == "HOST"]
    assert any("STOLE from Hero" in m for m in host_msgs)
