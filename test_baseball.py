import unittest
import random
from copy import deepcopy
from baseball import BaseballSimulator
from gameday_converter import GamedayConverter
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

        simulator = BaseballSimulator(home_team, away_team)
        gameday_data = simulator.play_game()
        converter = GamedayConverter(gameday_data)
        log = converter.convert()

        # Check for illegal pitching change for the away team (Pacific City)
        if "Top of Inning 9" in log and "Bottom of Inning 9" in log:
            pacific_city_batting_log = log.split("Top of Inning 9")[1].split("Bottom of Inning 9")[0]
            self.assertNotIn(f"--- Pitching Change for {away_team['name']}", pacific_city_batting_log)

        # Check for illegal pitching change for the home team (Bay Area)
        for i in range(1, 10):
            if f"Bottom of Inning {i}" in log and f"Top of Inning {i + 1}" in log:
                bottom_inning_log = log.split(f"Bottom of Inning {i}")[1].split(f"Top of Inning {i + 1}")[0]
                self.assertNotIn(f"--- Pitching Change for {home_team['name']}", bottom_inning_log)

    def test_for_complete_games(self):
        """Test for an unrealistically high number of complete games."""
        complete_games = 0
        num_simulations = 20

        for i in range(num_simulations):
            random.seed(i)
            simulator = BaseballSimulator(deepcopy(TEAMS["BAY_BOMBERS"]), deepcopy(TEAMS["PC_PILOTS"]))
            gameday_data = simulator.play_game()

            pitch_counts = {}
            for play in gameday_data['liveData']['plays']['allPlays']:
                pitcher_name = play['matchup']['pitcher']['fullName']
                if pitcher_name not in pitch_counts:
                    pitch_counts[pitcher_name] = 0
                pitch_counts[pitcher_name] += len(play['playEvents'])

            team1_pitchers_used = len([p for p in pitch_counts if p in [player['legal_name'] for player in TEAMS["BAY_BOMBERS"]['players']]])
            team2_pitchers_used = len([p for p in pitch_counts if p in [player['legal_name'] for player in TEAMS["PC_PILOTS"]['players']]])

            if team1_pitchers_used == 1 or team2_pitchers_used == 1:
                complete_games += 1

        self.assertLess(complete_games, num_simulations * 0.1, "Unrealistically high number of complete games found.")

    def test_event_variety(self):
        """Check for a variety of game events like walks, errors, and double plays."""
        events = {"Walk": 0, "Error": 0, "Double Play": 0}
        num_simulations = 20

        for i in range(num_simulations):
            random.seed(i)
            simulator = BaseballSimulator(deepcopy(TEAMS["BAY_BOMBERS"]), deepcopy(TEAMS["PC_PILOTS"]))
            gameday_data = simulator.play_game()
            converter = GamedayConverter(gameday_data)
            log = converter.convert()

            if "draws a walk" in log: events["Walk"] += 1
            if "An error allows" in log: events["Error"] += 1
            if "double play" in log.lower() or "Double Play" in log: events["Double Play"] += 1

        self.assertGreater(events["Walk"], 0, "No walks were recorded in the simulations.")
        self.assertGreater(events["Error"], 0, "No errors were recorded in the simulations.")
        self.assertGreater(events["Double Play"], 0, "No double plays were recorded in the simulations.")


if __name__ == '__main__':
    unittest.main()
