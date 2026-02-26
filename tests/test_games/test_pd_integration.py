from tests.helpers.game_test_helpers import build_pd_game, turn_payload


def test_full_pd_round_execution():
    game, board, _agents, clients = build_pd_game(
        {
            "Hero": [
                turn_payload(action="split", public_response="I trust you, let's split."),
                turn_payload(public_response="Noooo"),
            ],
            "Villain": [
                turn_payload(action="steal", public_response="Of course I will split!"),
                turn_payload(public_response="Worth it"),
            ],
        }
    )

    game.run_game_prisoners_dilemma(choose_partner=False)

    assert board.agent_scores["Hero"] == 0
    assert board.agent_scores["Villain"] == 5

    history = board.currentRound
    assert any("STOLE from Hero" in str(event) for event in history)
    clients["Hero"].assert_exhausted()
    clients["Villain"].assert_exhausted()
