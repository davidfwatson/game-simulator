import unittest
import random
import io
import re
from contextlib import redirect_stdout
from baseball import BaseballSimulator
from teams import TEAMS

class TestAnalystConcerns(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        # A fixed seed ensures that the tests are deterministic.
        random.seed(42)

    def _run_sim_and_get_log(self, num_games=1):
        """A helper method to run the simulation and capture its output."""
        log_capture = io.StringIO()
        with redirect_stdout(log_capture):
            for _ in range(num_games):
                # We re-initialize the game each time to reset the state
                game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])
                game.play_game()
        return log_capture.getvalue()

    def test_mechanical_phrasing_of_pitches(self):
        """
        Analyst Concern: Nearly every pitch says “in the strike zone” (or simple “inside/high/low”)
        with no granular location or Statcast-style variation.

        Test: This test runs a simulation and checks for a wider variety of pitch location descriptions.
        It will fail if only the basic, mechanical descriptions are found.
        """
        log = self._run_sim_and_get_log()

        # This pattern finds all pitch location descriptions in the log.
        # It looks for the text immediately following the pitch type and velocity.
        location_phrases = re.findall(r'\d+ mph\), (.*?)\.', log)

        # The original, mechanical phrases.
        basic_phrases = {"in the strike zone", "high", "low", "inside", "outside"}

        # We expect to find new, more descriptive phrases beyond the basic set.
        found_phrases = set(location_phrases)

        self.assertTrue(len(found_phrases) > len(basic_phrases),
                        f"Pitch phrasing is too mechanical. Found only: {found_phrases}")

    def test_unrealistic_outcome_distribution(self):
        """
        Analyst Concern: Unusually many infield popouts (P3/P5) relative to grounders/lineouts,
        and very few walks given the long pitch sequences.

        Test: This test simulates 100 games to check the distribution of outcomes.
        It will fail if infield popouts are too frequent compared to outfield flyouts
        or if the number of walks is unrealistically low.
        """
        log = self._run_sim_and_get_log(num_games=100)

        # Count popouts and flyouts using their more robust scoring notations.
        popouts = len(re.findall(r'\(P\d\)', log))
        flyouts = len(re.findall(r'\(F\d\)', log))

        # Count walks by looking for the unique phrasing in the new output.
        walks = log.count("a walk.")

        # In real baseball, outfield flyouts are significantly more common than infield popouts.
        self.assertTrue(flyouts > popouts * 1.5,
                        f"Unrealistic outcome distribution: {popouts} popouts vs. {flyouts} flyouts. "
                        "Expected more flyouts.")

        # A typical game has several walks. Over 100 games, we expect a healthy number.
        self.assertTrue(walks > 200, # Average of 2+ walks per game
                        f"Unrealistically low number of walks ({walks}) over 100 games. "
                        "Suggests flawed plate discipline logic.")

    def test_scoring_inconsistency_on_errors(self):
        """
        Analyst Concern: A fly ball logged as a “Flyout” followed by “Error” is odd—real
        scoring would record a reach-on-error, not a completed flyout plus error.

        Test: This test scans the game log for instances of an out being recorded immediately
        followed by an error announcement for the same play. It will fail if this
        incorrect scoring pattern is found.
        """
        log = self._run_sim_and_get_log(num_games=50) # More games to increase chance of an error

        # Split the log into individual at-bats to prevent cross-play matching.
        at_bats = log.split("Now batting:")[1:]

        for at_bat_log in at_bats:
            # Check if an out was recorded in the 'Result:' line of this at-bat.
            is_out = re.search(r'Result: (Flyout|Groundout|Pop out)', at_bat_log)
            # Check if an error was announced during this at-bat.
            is_error = "An error by" in at_bat_log

            if is_out and is_error:
                self.fail("Incorrectly logged an out and an error in the same at-bat."
                          f"\n---LOG---\nNow batting:{at_bat_log}\n----------")

    def test_velocity_regularity(self):
        """
        Analyst Concern: Fastballs clustered at neat integers (94–97) and secondaries at
        tidy bands (78–84, 86–90) with minimal drift.

        Test: This test checks if pitch velocities are all whole numbers.
        It will fail if no floating-point velocities (e.g., 94.3 mph) are found,
        indicating that the velocities are too regular and lack human-like variance.
        """
        log = self._run_sim_and_get_log()

        # This pattern finds all velocities, including those with decimal points.
        velocities = re.findall(r'\((\d{2,3}(?:\.\d)?) mph\)', log)

        # Check if any of the found velocities contain a decimal point.
        has_float_velocities = any('.' in v for v in velocities)

        self.assertTrue(has_float_velocities,
                        "Pitch velocities are too regular and only use integers. "
                        "Expected floating-point values for more realism.")

    def test_groundout_to_catcher_frequency(self):
        """
        Analyst Concern: Unusual frequency of 2–3 groundouts (catcher to first).

        Test: Simulates many games and fails if the number of 2-3 groundouts
        is not significantly lower than groundouts to other infielders.
        """
        log = self._run_sim_and_get_log(num_games=100)

        # Count groundouts by fielder position from the notation (e.g., " (6-3)")
        groundouts_to_ss = log.count("(6-3)")
        groundouts_to_2b = log.count("(4-3)")
        groundouts_to_3b = log.count("(5-3)")
        groundouts_to_c = log.count("(2-3)") # The unusual play

        total_infield_groundouts = groundouts_to_ss + groundouts_to_2b + groundouts_to_3b

        # A 2-3 groundout is rare. We expect far fewer than to any other infielder.
        # Let's assert it's less than 20% of the average for other infielders.
        # This is a heuristic that should fail the current implementation.
        is_unrealistic = groundouts_to_c > (total_infield_groundouts / 3) * 0.5
        self.assertFalse(is_unrealistic,
                        f"Unrealistic frequency of 2-3 groundouts. Catcher: {groundouts_to_c}, "
                        f"SS: {groundouts_to_ss}, 2B: {groundouts_to_2b}, 3B: {groundouts_to_3b}")

    def test_for_template_phrasing(self):
        """
        Analyst Concern: Template-y phrasing, especially "In play -> ...".

        Test: This test fails if the rigid "In play ->" structure is found in the log.
        """
        log = self._run_sim_and_get_log()
        self.assertNotIn("In play ->", log, "Found rigid 'In play ->' phrasing.")

    def test_bullpen_usage_variability(self):
        """
        Analyst Concern: Identical bullpen script across games.

        Test: Runs two separate games and asserts that the pitching changes are not identical.
        """
        # Run game 1 and capture its pitching changes
        log1 = self._run_sim_and_get_log(num_games=1)
        changes1 = re.findall(r"--- Pitching Change for (.+?) ---", log1)

        # Run game 2 and capture its pitching changes.
        # The random state will be different from the start of game 1 because setUp does not re-seed
        # in a way that would make two consecutive calls identical within the same test run.
        log2 = self._run_sim_and_get_log(num_games=1)
        changes2 = re.findall(r"--- Pitching Change for (.+?) ---", log2)

        self.assertNotEqual(changes1, changes2,
                            "Bullpen usage was identical in two consecutive simulated games.")

    def test_extra_innings_message_style(self):
        """
        Analyst Concern: The extra-innings banner feels like a synthetic UI message.

        Test: This test fails if the hardcoded, UI-like extra innings banner is found.
        """
        # Run enough games to make extra innings likely
        log = self._run_sim_and_get_log(num_games=50)

        # The test passes if no extra inning game occurs, which is acceptable.
        # If one does, it must not contain the synthetic banner.
        match = re.search(r"--- Extra Innings: (.+?) placed on second base. ---", log)
        self.assertIsNone(match, "Found synthetic extra-innings banner in the log.")


if __name__ == '__main__':
    unittest.main()