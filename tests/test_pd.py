import pytest



def test_split_vs_steal_logic(pd_game):
    """
    Verifies the scoring logic for the Prisoner's Dilemma payout matrix.
    The 'pd_game' argument is automatically injected by the fixture in conftest.py.
    """
    
    # Define test cases: (Choice A, Choice B, Points A, Points B, Description)
    scenarios = [
        ("split", "split",   3, 3, "Both Split (Cooperation)"),
        ("steal", "steal",   1, 1, "Both Steal (Defection)"),
        ("steal", "split",   5, 0, "A Steals, B Splits (Betrayal)"),
        ("split", "steal",   0, 5, "A Splits, B Steals (Victim)"),
        ("mumble", "split",  0, 0, "Hallucinated Move (Invalid Input)"),
        ("SPLIT.", "split ", 3, 3, "Messy Input (Sanitization Check)"),
    ]

    print("\n----------------------------------------------------------------")
    print(f"Testing Payout Matrix logic on: {pd_game.__class__.__name__}")
    
    for c0, c1, exp0, exp1, desc in scenarios:
        # Act
        # calling the helper method we refactored earlier
        p0, p1, msg = pd_game._calculate_pd_payout(c0, c1, "AgentA", "AgentB")

        # Assert
        error_msg = f"Failed on case: {desc} | Input: {c0} vs {c1}"
        assert p0 == exp0, f"{error_msg} -> Agent A got {p0}, expected {exp0}"
        assert p1 == exp1, f"{error_msg} -> Agent B got {p1}, expected {exp1}"

        # Logic checks for the message
        if "Hallucinated" in desc:
            assert "hallucinated" in msg
        elif c0.lower().startswith("steal") and c1.lower().startswith("split"):
             assert "STOLE from" in msg

    print("✅ All Prisoner's Dilemma logic tests passed!")