import unittest
import random
import io
from copy import deepcopy
from contextlib import redirect_stdout
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS

class TestBaseballRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)

    def test_impossible_pitching_change(self):
        """Verify that a team cannot make a pitching change while batting."""
        home_team = deepcopy(TEAMS["BAY_BOMBERS"])
        away_team = deepcopy(TEAMS["PC_PILOTS"])

        # Force a situation where a pitching change is likely
        home_team['players'][9]['stamina'] = 1
        away_team['players'][9]['stamina'] = 1

        game = BaseballSimulator(home_team, away_team)
        game.play_game()

        renderer = NarrativeRenderer(game.gameday_data, seed=42)
        log = renderer.render()

        # Check for illegal pitching change for the away team (Pacific City)
        if "Top of Inning 9" in log and "Bottom of Inning 9" in log:
            pacific_city_batting_log = log.split("Top of Inning 9")[1].split("Bottom of Inning 9")[0]
            self.assertNotIn(f"--- Pitching Change for {away_team['name']}", pacific_city_batting_log)

        # Check for illegal pitching change for the home team (Bay Area)
        for i in range(1, 10):
            if f"Bottom of Inning {i}" in log and f"Top of Inning {i+1}" in log:
                bottom_inning_log = log.split(f"Bottom of Inning {i}")[1].split(f"Top of Inning {i+1}")[0]
                self.assertNotIn(f"--- Pitching Change for {home_team['name']}", bottom_inning_log)

    def test_for_complete_games(self):
        """Test for an unrealistically high number of complete games."""
        complete_games = 0
        num_simulations = 20

        for i in range(num_simulations):
            game = BaseballSimulator(deepcopy(TEAMS["BAY_BOMBERS"]), deepcopy(TEAMS["PC_PILOTS"]), game_seed=i)
            game.play_game()

            team1_pitchers_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team1_pitcher_stats])
            team2_pitchers_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team2_pitcher_stats])

            if team1_pitchers_used == 1 or team2_pitchers_used == 1:
                complete_games += 1

        self.assertLess(complete_games, num_simulations * 0.1, "Unrealistically high number of complete games found.")

    def test_event_variety(self):
        """Check for a variety of game events like walks, errors, and double plays."""
        events = {"Walk": 0, "Error": 0, "Double Play": 0}
        num_simulations = 20

        for i in range(num_simulations):
            game = BaseballSimulator(deepcopy(TEAMS["BAY_BOMBERS"]), deepcopy(TEAMS["PC_PILOTS"]), game_seed=i)
            game.play_game()

            renderer = NarrativeRenderer(game.gameday_data, seed=i)
            log = renderer.render()

            if "draws a walk" in log: events["Walk"] += 1
            if "error" in log.lower() or "bobbles" in log or "drops it" in log or "clanks" in log or "tips off" in log: events["Error"] += 1 # Adjusted for flexible checking
            if "double play" in log.lower() or "Double Play" in log: events["Double Play"] += 1

        self.assertGreater(events["Walk"], 0, "No walks were recorded in the simulations.")
        self.assertGreater(events["Error"], 0, "No errors were recorded in the simulations.")
        self.assertGreater(events["Double Play"], 0, "No double plays were recorded in the simulations.")

if __name__ == '__main__':
    unittest.main()