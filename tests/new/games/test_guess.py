from gameplay_management.eliminations.voting_lowest_points import VoteLowestPoints
from tests.new.helpers import guess_with_number, start_game


def test_a_correct_guess_wins_the_full_award():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    assert game.score("Ada") == 4


def test_a_wrong_guess_scores_nothing():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    assert game.score("Bo") == 0


def test_two_correct_guessers_each_win_the_full_award():
    game = start_game(players=["Ada", "Bo", "Cy"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="3")
    game.chooses("Cy", choice="1")

    game.run()

    assert game.score("Ada") == 4
    assert game.score("Bo") == 4


def test_nobody_scores_when_everybody_guesses_wrong():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="1")
    game.chooses("Bo", choice="2")

    game.run()

    assert game.score("Ada") == 0
    assert game.score("Bo") == 0


def test_everybody_wins_when_there_is_only_one_number_to_guess():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(1)])
    game.configure("set_guess_range", 1)
    game.chooses("Ada", choice="1")
    game.chooses("Bo", choice="1")

    game.run()

    assert game.score("Ada") == 1
    assert game.score("Bo") == 1


def test_the_widget_marks_who_was_right_and_what_they_won():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    rows = {row["name"]: row for row in game.widgets("guess")[-1]["rows"]}
    assert rows["Ada"]["correct"] is True
    assert rows["Ada"]["points"] == 4
    assert rows["Bo"]["correct"] is False
    assert rows["Bo"]["points"] is None


def test_the_widget_records_each_revealed_guess():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    rows = {row["name"]: row for row in game.widgets("guess")[-1]["rows"]}
    assert rows["Ada"]["guess"] == 3
    assert rows["Bo"]["guess"] == 1
    assert all(row["state"] == "revealed" for row in rows.values())


def test_the_widget_range_follows_the_configured_range():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    assert game.widgets("guess")[0]["range"] == {"min": 1, "max": 4}


def test_no_guess_is_visible_before_the_reveal():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    payloads = game.widgets("guess")
    assert payloads
    for payload in payloads:
        if any(row["state"] == "revealed" for row in payload["rows"]):
            break
        assert all(row["guess"] is None for row in payload["rows"])


def test_the_wrong_guesser_is_voted_out_on_points():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3), VoteLowestPoints])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    assert game.eliminated() == ["Bo"]
    assert game.winner() == "Ada"


def test_a_revealed_guess_arrives_with_the_guessers_own_message():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    rows = {row["name"]: row for row in game.widget_shown_with("Ada")["rows"]}
    assert rows["Ada"]["state"] == "revealed"
    assert rows["Ada"]["guess"] == 3
    assert rows["Bo"]["state"] != "revealed"


def test_the_result_widget_arrives_with_the_hosts_result_message():
    game = start_game(players=["Ada", "Bo"], rounds=[guess_with_number(3)])
    game.configure("set_guess_range", 4)
    game.chooses("Ada", choice="3")
    game.chooses("Bo", choice="1")

    game.run()

    rows = {row["name"]: row for row in game.widget_shown_with("HOST")["rows"]}
    assert rows["Ada"]["correct"] is True
    assert rows["Ada"]["points"] == 4
    assert rows["Bo"]["correct"] is False
