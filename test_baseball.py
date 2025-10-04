import unittest
import random
import io
from contextlib import redirect_stdout
from baseball import BaseballSimulator
from teams import TEAMS

class TestBaseballRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)

    def test_impossible_pitching_change(self):
        """Verify that a team cannot make a pitching change while batting."""
        home_team = TEAMS["BAY_BOMBERS"]
        away_team = TEAMS["PC_PILOTS"]

        # Force a situation where a pitching change is likely
        # Set starter stamina to a very low value
        home_team['players'][9]['stamina'] = 1
        away_team['players'][9]['stamina'] = 1

        game = BaseballSimulator(home_team, away_team)

        output = io.StringIO()
        with redirect_stdout(output):
            game.play_game()

        log = output.getvalue()

        # Check for illegal pitching change for the away team (Pacific City)
        pacific_city_batting_log = log.split("Top of Inning 9")[1].split("Bottom of Inning 9")[0]
        self.assertNotIn(f"--- Pitching Change for {away_team['name']}", pacific_city_batting_log)

        # Check for illegal pitching change for the home team (Bay Area)
        # This is harder to test directly as the game might end, but we can check the whole log
        # A home team pitching change should not happen in the bottom of an inning.
        for i in range(1, 10):
            if f"Bottom of Inning {i}" in log:
                bottom_inning_log = log.split(f"Bottom of Inning {i}")[1].split(f"Top of Inning {i+1}")[0]
                self.assertNotIn(f"--- Pitching Change for {home_team['name']}", bottom_inning_log)


    def test_for_complete_games(self):
        """Test for an unrealistically high number of complete games."""
        complete_games = 0
        num_simulations = 20 # Reduced from 100 for speed, but still effective

        for i in range(num_simulations):
            random.seed(i) # Use different seed for each game
            game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])

            # Suppress output during simulation
            with redirect_stdout(io.StringIO()):
                game.play_game()

            # Check if either starter pitched a complete game
            team1_pitcher_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team1_pitcher_stats])
            team2_pitcher_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team2_pitcher_stats])

            if team1_pitcher_used == 1 or team2_pitcher_used == 1:
                complete_games += 1

        # This assertion will likely fail, as the number of complete games is expected to be high.
        # A realistic threshold for modern baseball would be very low, e.g., less than 5% of games.
        self.assertLess(complete_games, num_simulations * 0.1, "Unrealistically high number of complete games found.")

    def test_event_variety(self):
        """Check for a variety of game events like walks, errors, and double plays."""
        events = {"Walk": 0, "Error": 0, "Double Play": 0}
        num_simulations = 20

        for i in range(num_simulations):
            random.seed(i)
            game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])

            output = io.StringIO()
            with redirect_stdout(output):
                game.play_game()

            log = output.getvalue()

            if "a walk" in log: events["Walk"] += 1
            if "Error" in log: events["Error"] += 1
            if "Double Play" in log: events["Double Play"] += 1

        self.assertGreater(events["Walk"], 0, "No walks were recorded in the simulations.")
        self.assertGreater(events["Error"], 0, "No errors were recorded in the simulations.")
        self.assertGreater(events["Double Play"], 0, "No double plays were recorded in the simulations.")

if __name__ == '__main__':
    unittest.main()