from types import SimpleNamespace
from unittest.mock import MagicMock

def test_run_pd_odd_player_gets_auto_split_points(pd_game):
    """Odd leftover player should get automatic split points and not be prompted."""
    a1 = MagicMock(name="A1")
    a1.name = "A1"
    a2 = MagicMock(name="A2")
    a2.name = "A2"
    a3 = MagicMock(name="A3")
    a3.name = "A3"

    pd_game.simulationEngine.agents = [a1, a2, a3]

    pd_game._generate_pairings = MagicMock(return_value=([(a1, a2)], a3))
    pd_game.get_split_or_steal = MagicMock(
        side_effect=[SimpleNamespace(action="split"), SimpleNamespace(action="split")]
    )
    pd_game.publicPrivateResponse = MagicMock()
    pd_game.respond_to = MagicMock(return_value=SimpleNamespace())

    pd_game.run_game_prisoners_dilemma(choose_partner=False)

    pd_game.gameBoard.append_agent_points.assert_any_call("A3", 3)
    assert pd_game.get_split_or_steal.call_count == 2


def test_run_pd_passes_manual_pairing_flags(pd_game):
    """Choose-partner mode should pass both flags into pairing generation."""
    p1 = MagicMock()
    p1.name = "P1"
    p2 = MagicMock()
    p2.name = "P2"

    pd_game.simulationEngine.agents = [p1, p2]

    pd_game._generate_pairings = MagicMock(return_value=([(p1, p2)], None))
    pd_game.get_split_or_steal = MagicMock(
        side_effect=[SimpleNamespace(action="split"), SimpleNamespace(action="steal")]
    )
    pd_game.publicPrivateResponse = MagicMock()
    pd_game.respond_to = MagicMock(return_value=SimpleNamespace())

    pd_game.run_game_prisoners_dilemma(choose_partner=True, winner_picks_first=False)

    args, _ = pd_game._generate_pairings.call_args
    assert args[1] is True
    assert args[2] is False


def test_run_pd_collects_decisions_and_reactions_for_each_player(pd_game):
    """Each pair should publish 2 decisions and 2 reactions via publicPrivateResponse."""
    h = MagicMock()
    h.name = "Hero"
    v = MagicMock()
    v.name = "Villain"

    pd_game.simulationEngine.agents = [h, v]
    pd_game._generate_pairings = MagicMock(return_value=([(h, v)], None))

    hero_decision = SimpleNamespace(action="split")
    villain_decision = SimpleNamespace(action="steal")
    pd_game.get_split_or_steal = MagicMock(side_effect=[hero_decision, villain_decision])

    hero_reaction = SimpleNamespace(public_response="Noooo")
    villain_reaction = SimpleNamespace(public_response="Worth it")
    pd_game.respond_to = MagicMock(side_effect=[hero_reaction, villain_reaction])

    pd_game.publicPrivateResponse = MagicMock()

    pd_game.run_game_prisoners_dilemma(choose_partner=False)

    assert pd_game.publicPrivateResponse.call_count == 4
    pd_game.publicPrivateResponse.assert_any_call(h, hero_decision)
    pd_game.publicPrivateResponse.assert_any_call(v, villain_decision)
    pd_game.publicPrivateResponse.assert_any_call(h, hero_reaction)
    pd_game.publicPrivateResponse.assert_any_call(v, villain_reaction)