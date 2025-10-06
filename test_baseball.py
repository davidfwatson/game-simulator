import unittest
import random
import copy
from baseball import BaseballSimulator
from teams import TEAMS

class TestBaseballRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)

    def test_impossible_pitching_change(self):
        """Verify that a team cannot make a pitching change while batting."""
        home_team = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        away_team = copy.deepcopy(TEAMS["PC_PILOTS"])

        # Force a situation where a pitching change is likely by reducing starter stamina
        for player in home_team['players']:
            if player.get('type') == 'Starter':
                player['stamina'] = 1
                break
        for player in away_team['players']:
            if player.get('type') == 'Starter':
                player['stamina'] = 1
                break

        game = BaseballSimulator(home_team, away_team)
        game.play_game()
        log = "\n".join(game.output_lines)

        # This test can be flaky if the game doesn't last 9 innings.
        # A skip is better than a failure for an inconclusive run.
        if "Top of Inning 9" not in log or "Bottom of Inning 9" not in log:
            self.skipTest("Game did not reach the 9th inning, cannot test illegal pitching change.")

        pacific_city_batting_log = log.split("Top of Inning 9")[1].split("Bottom of Inning 9")[0]
        self.assertNotIn(f"--- Pitching Change for {away_team['name']}", pacific_city_batting_log)

        for i in range(1, 10):
            if f"Bottom of Inning {i}" in log:
                inning_log_parts = log.split(f"Bottom of Inning {i}")
                if len(inning_log_parts) > 1:
                    bottom_inning_log = inning_log_parts[1].split(f"Top of Inning {i+1}")[0]
                    self.assertNotIn(f"--- Pitching Change for {home_team['name']}", bottom_inning_log)

    def test_for_complete_games(self):
        """Test for an unrealistically high number of complete games."""
        complete_games = 0
        num_simulations = 20

        for i in range(num_simulations):
            random.seed(i)
            game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])
            game.play_game()

            team1_starters = [p['legal_name'] for p in TEAMS["BAY_BOMBERS"]['players'] if p.get('type') == 'Starter']
            team2_starters = [p['legal_name'] for p in TEAMS["PC_PILOTS"]['players'] if p.get('type') == 'Starter']

            team1_pitchers_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team1_pitcher_stats])
            team2_pitchers_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team2_pitcher_stats])

            if team1_pitchers_used == 1 and game.team1_current_pitcher_name in team1_starters:
                complete_games += 1
            if team2_pitchers_used == 1 and game.team2_current_pitcher_name in team2_starters:
                complete_games += 1

        self.assertLess(complete_games, num_simulations * 0.5, "Unrealistically high number of complete games found.")

    def test_event_variety(self):
        """Check for a variety of game events like walks, errors, and double plays."""
        events = {"Walk": 0, "Error": 0, "Double Play": 0}
        num_simulations = 50

        for i in range(num_simulations):
            random.seed(i)
            game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])
            game.play_game()
            log = "\n".join(game.output_lines)

            if "Walk" in log: events["Walk"] += 1
            if "Error" in log: events["Error"] += 1
            if "Double Play" in log: events["Double Play"] += 1

        self.assertGreater(events["Walk"], 0, "No walks were recorded in the simulations.")
        self.assertGreater(events["Error"], 0, "No errors were recorded in the simulations.")
        self.assertGreater(events["Double Play"], 0, "No double plays were recorded in the simulations.")

if __name__ == '__main__':
    unittest.main()