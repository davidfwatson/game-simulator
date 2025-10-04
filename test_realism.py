import unittest
import random
import io
import re
from contextlib import redirect_stdout
from baseball import BaseballSimulator
from teams import TEAMS

class TestRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)
        self.home_team = TEAMS["BAY_BOMBERS"]
        self.away_team = TEAMS["PC_PILOTS"]

        # Capture the game output for a standard game
        output = io.StringIO()
        with redirect_stdout(output):
            game = BaseballSimulator(self.home_team, self.away_team)
            game.play_game()
        self.log = output.getvalue()

    def test_quantized_velocities(self):
        """Test if pitch velocities are too uniform or 'quantized'."""
        # This pattern now correctly captures integer and float velocities.
        velocities = re.findall(r'\((\d{2,3}(?:\.\d)?) mph\)', self.log)
        self.assertGreater(len(velocities), 0, "No velocities found in game log.")
        unique_velocities = set(map(float, velocities))
        # Expecting more than 10 unique velocities in a full game for realism.
        self.assertGreater(len(unique_velocities), 10, "Pitch velocities appear quantized and not varied enough.")

    def test_repetitive_phrasing(self):
        """Test for repetitive phrasing in play-by-play output. This should be the default behavior."""
        pitch_lines = re.findall(r'^\s*Pitch:.*', self.log, re.MULTILINE)
        # This regex matches the old, repetitive template. We check that not all lines match it.
        template = r"\s*Pitch: \w+ \(\d+ mph\)\."
        matching_lines = [line for line in pitch_lines if re.match(template, line)]

        # This assertion will fail if the phrasing is too simple (i.e., verbose_phrasing=False)
        # or if no pitch lines are found at all.
        self.assertGreater(len(pitch_lines), 0, "No pitch lines found in the log.")
        self.assertNotEqual(len(pitch_lines), len(matching_lines), "Play-by-play phrasing is too repetitive or simple.")

    def test_abstract_outcomes(self):
        """Test for abstract outcomes instead of specific scorer's notation."""
        # This test will fail if generic "Groundout" or "Flyout" are found.
        # The goal is to replace them with e.g., "Groundout (6-3)" or "Flyout to RF (F9)".
        self.assertFalse(re.search(r'Groundout\.', self.log), "Abstract 'Groundout.' found. Use scorer's notation.")
        self.assertFalse(re.search(r'Flyout\.', self.log), "Abstract 'Flyout.' found. Use scorer's notation.")

        # Check for the presence of fielder credit in the output
        has_fielder_credit = re.search(r'(to [A-Za-z ]+ Field|to [A-Za-z ]+ Baseman|to Pitcher|to Catcher|to Shortstop|\([1-9-]+\)|\(F\d+\))', self.log)
        self.assertIsNotNone(has_fielder_credit, "Outcomes lack specific fielder information.")

    def test_box_state_ui(self):
        """Test for the presence of the unrealistic '[1B]-[2B]-[3B]' base state UI."""
        self.assertNotIn("[1B]-[2B]-[3B]", self.log, "Unrealistic box-state UI is present.")

    def test_extra_innings_banner(self):
        """Test for unrealistic extra-innings banner text."""
        extra_inning_log = ""
        # Try a few seeds to find a game that goes to extra innings.
        for i in range(10):
            random.seed(i)
            output = io.StringIO()
            with redirect_stdout(output):
                game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])
                game.play_game()
            log = output.getvalue()
            if "Extra Innings" in log:
                extra_inning_log = log
                break

        if extra_inning_log:
            self.assertNotIn("--- Extra Innings: Runner placed on second base ---", extra_inning_log, "Unrealistic extra-innings banner found.")

    def test_nicknames_in_substitutions(self):
        """Test for the use of nicknames in substitution announcements, which is unrealistic."""
        sub_lines = re.findall(r'--- Pitching Change for.*', self.log)
        pitchers_with_nicknames = [p for p in self.home_team['players'] + self.away_team['players'] if p['position'] == 'P' and p.get('nickname')]

        # Ensure there are pitchers with nicknames to test against.
        self.assertTrue(len(pitchers_with_nicknames) > 0, "No pitchers with nicknames found for testing.")

        for line in sub_lines:
            for pitcher in pitchers_with_nicknames:
                # Assert that the nickname is NOT in the announcement.
                self.assertNotIn(f"'{pitcher['nickname']}'", line, f"Nickname '{pitcher['nickname']}' found in substitution announcement: {line}")
                self.assertNotIn(f" {pitcher['nickname']} ", line, f"Nickname '{pitcher['nickname']}' found in substitution announcement: {line}")

    def test_game_context_missing(self):
        """Test if essential game context like umpires, venue, and weather is missing."""
        self.assertIn("Umpires:", self.log, "Umpire information is missing from the pre-game summary.")
        self.assertIn("Weather:", self.log, "Weather information is missing from the pre-game summary.")
        self.assertIn("Venue:", self.log, "Venue information is missing from the pre-game summary.")

    def test_bracketed_ui_flag(self):
        """Test that the bracketed UI flag correctly changes the base runner display."""
        # Test with bracketed UI enabled
        output = io.StringIO()
        with redirect_stdout(output):
            game = BaseballSimulator(self.home_team, self.away_team, use_bracketed_ui=True)
            game.play_game()
        log_bracketed = output.getvalue()
        self.assertIn("[", log_bracketed, "Bracketed UI not found when flag is enabled.")
        self.assertIn("]-", log_bracketed, "Bracketed UI not found when flag is enabled.")

        # Test with bracketed UI disabled (default)
        output = io.StringIO()
        with redirect_stdout(output):
            game = BaseballSimulator(self.home_team, self.away_team, use_bracketed_ui=False)
            game.play_game()
        log_named = output.getvalue()
        self.assertNotIn("[", log_named, "Bracketed UI found when flag is disabled.")
        self.assertNotIn("]-", log_named, "Bracketed UI found when flag is disabled.")

    def test_simulation_realism_over_multiple_games(self):
        """
        Run the simulation multiple times to check for realism issues identified by the analyst.
        This test aggregates data over 100 simulated games to ensure a reasonable distribution
        of game events like walks, HBPs, DPs, and specific out types.
        """
        num_games = 100
        total_walks, total_hbps, total_dps, total_triples = 0, 0, 0, 0
        groundout_2_3_count, unassisted_3u_count = 0, 0
        flyouts, popouts = 0, 0

        for i in range(num_games):
            random.seed(i)  # Use a different seed for each game to get varied outcomes
            output = io.StringIO()
            with redirect_stdout(output):
                game = BaseballSimulator(self.home_team, self.away_team)
                game.play_game()
            log = output.getvalue()

            total_walks += log.count("Result: Walk")
            total_hbps += log.count("Hit by Pitch")
            total_dps += log.count("Double Play")
            total_triples += log.count("Result: Triple")
            groundout_2_3_count += len(re.findall(r'Groundout to Catcher \(2-3\)', log))
            unassisted_3u_count += len(re.findall(r'Groundout to 1B \(3U\)', log))

            # Differentiate flyouts (outfield) from popouts (infield)
            flyouts += len(re.findall(r'Flyout to (LF|CF|RF)', log))
            popouts += len(re.findall(r'Pop out to (P|C|1B|2B|3B|SS)', log))

        # Asserts are based on what would be expected over 100 games.
        # These will likely fail with the current simulation engine.

        # 1. Walks should be present, averaging at least a few per game.
        self.assertGreater(total_walks, 50, "Very few walks over 100 games, indicates a problem with plate discipline logic.")

        # 2. HBPs, while rare, should occur.
        self.assertGreater(total_hbps, 2, "Hit by pitches are missing from the simulation.")

        # 3. Double plays are a common feature of real games.
        self.assertGreater(total_dps, 20, "Double plays are too rare or missing.")

        # 4. Triples should not be overly common.
        self.assertLess(total_triples, 30, "Too many triples, indicates an issue with hit outcome distribution.")

        # 5. The 2-3 groundout should be very rare.
        self.assertLess(groundout_2_3_count, 5, "Unrealistically high number of 2-3 groundouts.")

        # 6. Unassisted 3U groundouts should be the standard for a 1B.
        self.assertGreater(unassisted_3u_count, 10, "3U unassisted groundouts are not being logged correctly.")

        # 7. Pop outs to infielders should be labeled correctly.
        self.assertGreater(popouts, 10, "Infield fly balls are not being classified as 'Pop outs'.")
        self.assertGreater(flyouts, 10, "Outfield fly balls are not being classified as 'Flyouts'.")


    def test_no_wp_or_pb_with_bases_empty(self):
        """
        Test that a wild pitch or passed ball does not occur when the bases are empty.
        This test runs the simulation multiple times to ensure the probabilistic check is robust.
        """
        for i in range(50):  # Run multiple games to increase the chance of encountering the event
            random.seed(i)
            output = io.StringIO()
            with redirect_stdout(output):
                game = BaseballSimulator(self.home_team, self.away_team)
                game.play_game()
            log = output.getvalue()

            lines = log.split('\n')
            last_bases_state = ""
            for line in lines:
                # Track the state of the bases from the end of each at-bat
                if line.strip().startswith("Result:"):
                    if "Bases: " in line:
                        # Extract the base state string, e.g., "Bases empty" or "1B: Player"
                        last_bases_state = line.split("Bases: ")[1].split(" | ")[0]

                # If a WP or PB occurs, check the last known state of the bases
                if "Wild Pitch!" in line or "Passed Ball!" in line:
                    self.assertNotEqual(last_bases_state, "Bases empty",
                                        f"Impossible event: A wild pitch or passed ball occurred with the bases empty.\nLog Line: {line}")


if __name__ == '__main__':
    unittest.main()