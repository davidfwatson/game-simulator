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

            if "Walk" in log: events["Walk"] += 1
            if "Error" in log: events["Error"] += 1
            if "Double Play" in log: events["Double Play"] += 1

        self.assertGreater(events["Walk"], 0, "No walks were recorded in the simulations.")
        self.assertGreater(events["Error"], 0, "No errors were recorded in the simulations.")
        self.assertGreater(events["Double Play"], 0, "No double plays were recorded in the simulations.")

if __name__ == '__main__':
    unittest.main()

class TestRealismTelltales(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)  # Reset seed for each test to prevent pollution
        self.home_team = TEAMS["BAY_BOMBERS"]
        self.away_team = TEAMS["PC_PILOTS"]

    def _run_one_inning_simulation(self, game):
        """Helper to run a single inning and capture output."""
        output = io.StringIO()
        with redirect_stdout(output):
            game._simulate_half_inning()
        return output.getvalue()

    def _run_full_game_simulation(self, game):
        """Helper to run a full game and capture output."""
        output = io.StringIO()
        with redirect_stdout(output):
            game.play_game()
        return output.getvalue()

    def test_quantized_velocities(self):
        """Test if pitch velocities show realistic variation."""
        game = BaseballSimulator(self.home_team, self.away_team)
        log = self._run_full_game_simulation(game)

        velocities = [int(line.split('(')[1].split(' mph')[0]) for line in log.split('\n') if 'mph' in line]
        unique_velocities = set(velocities)

        self.assertGreaterEqual(len(unique_velocities), 5, "Pitch velocities are not sufficiently varied.")

    def test_repetitive_phrasing(self):
        """Test for variation in play-by-play phrasing."""
        game_varied = BaseballSimulator(self.home_team, self.away_team, varied_phrasing=True)
        log_varied = self._run_one_inning_simulation(game_varied)

        game_standard = BaseballSimulator(self.home_team, self.away_team, varied_phrasing=False)
        log_standard = self._run_one_inning_simulation(game_standard)

        standard_pitch_lines = [line.strip() for line in log_standard.split('\n') if 'Pitch:' in line]
        varied_pitch_lines = [line.strip() for line in log_varied.split('\n') if 'comes in at' in line]

        self.assertTrue(all(line.startswith('Pitch:') for line in standard_pitch_lines), "Standard pitch phrasing is incorrect.")
        self.assertFalse(any(line.startswith('Pitch:') for line in varied_pitch_lines), "Varied phrasing should not use the standard format.")

    def test_abstract_outcomes(self):
        """Test for specific scorer codes in outcomes instead of generic terms."""
        game = BaseballSimulator(self.home_team, self.away_team)
        log = self._run_full_game_simulation(game)

        self.assertRegex(log, r"Groundout \(\d-\d\)", "Groundout descriptions lack scorer codes.")
        self.assertRegex(log, r"Flyout \(F\d\)", "Flyout descriptions lack fielder codes.")

    def test_box_state_ui_realism(self):
        """Test for narrative vs. standard representation of runners on base."""
        game_varied = BaseballSimulator(self.home_team, self.away_team, varied_phrasing=True)
        game_standard = BaseballSimulator(self.home_team, self.away_team, varied_phrasing=False)

        # Test varied, narrative phrasing
        game_varied.bases = [1, 0, 1] # Man on first and third
        self.assertEqual(game_varied._get_bases_str(), "Runners on the corners", "Narrative for runners on corners is incorrect.")
        game_varied.bases = [1, 1, 1]
        self.assertEqual(game_varied._get_bases_str(), "Bases loaded", "Narrative for bases loaded is incorrect.")

        # Test standard, HUD-style phrasing
        game_standard.bases = [1, 0, 1]
        self.assertEqual(game_standard._get_bases_str(), "Bases: [1B]-[_]-[3B]", "Standard base state UI is incorrect for runners on corners.")
        game_standard.bases = [0, 1, 0]
        self.assertEqual(game_standard._get_bases_str(), "Bases: [_]-[2B]-[_]", "Standard base state UI is incorrect for runner on second.")

    def test_extra_innings_banner_realism(self):
        """Test that the extra-innings banner is formatted realistically."""
        game = BaseballSimulator(self.home_team, self.away_team)
        game.inning = 10
        log = self._run_one_inning_simulation(game)

        self.assertNotIn("--- Extra Innings: Runner placed on second base ---", log)
        self.assertIn("Runner on second to start the inning.", log, "Extra innings banner is not realistic.")

    def test_nickname_usage(self):
        """Test that player introductions use legal names, not just nicknames."""
        game = BaseballSimulator(self.home_team, self.away_team)

        # Force a pitching change
        game.pitch_counts[game.team1_current_pitcher_name] = 100

        log = self._run_one_inning_simulation(game)

        # The starter is "Joe Gibson", the reliever is "Miller"
        self.assertIn("Now pitching, Miller", log, "Reliever introduction should use legal name.")
        self.assertNotIn("Now pitching, 'Cyclone'", log, "Reliever introduction should not use nickname.")