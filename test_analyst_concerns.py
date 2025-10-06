import unittest
import random
import io
import re
from baseball import BaseballSimulator
from teams import TEAMS

class TestAnalystConcerns(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)

    def _run_sim_and_get_log(self, num_games=1, **kwargs):
        """A helper method to run the simulation and capture its output."""
        full_log = ""
        for i in range(num_games):
            random.seed(i)
            # We re-initialize the game each time to reset the state
            game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"], **kwargs)
            game.play_game()
            full_log += "\n".join(game.output_lines)
        return full_log

    def test_mechanical_phrasing_of_pitches(self):
        """
        Analyst Concern: Nearly every pitch says “in the strike zone” (or simple “inside/high/low”)
        with no granular location or Statcast-style variation.
        """
        log = self._run_sim_and_get_log(verbose_phrasing=True)
        location_phrases = re.findall(r'\d+ mph\), (.*?)\.', log)
        basic_phrases = {"in the strike zone", "high", "low", "inside", "outside"}
        found_phrases = set(location_phrases)
        self.assertTrue(len(found_phrases) > len(basic_phrases),
                        f"Pitch phrasing is too mechanical. Found only: {found_phrases}")

    def test_unrealistic_outcome_distribution(self):
        """
        Analyst Concern: Unusually many infield popouts (P3/P5) relative to grounders/lineouts,
        and very few walks given the long pitch sequences.
        """
        log = self._run_sim_and_get_log(num_games=100)
        popouts = len(re.findall(r'Pop out to (C|P|1B|2B|3B|SS)', log))
        flyouts = len(re.findall(r'Flyout to (LF|CF|RF)', log))
        walks = log.count("Result: Walk")
        self.assertTrue(flyouts > popouts * 1.5,
                        f"Unrealistic outcome distribution: {popouts} popouts vs. {flyouts} flyouts.")
        self.assertTrue(walks > 200,
                        f"Unrealistically low number of walks ({walks}) over 100 games.")

    def test_scoring_inconsistency_on_errors(self):
        """
        Analyst Concern: A fly ball logged as a “Flyout” followed by “Error” is odd.
        """
        log = self._run_sim_and_get_log(num_games=50)
        at_bats = log.split("Now batting:")[1:]
        for at_bat_log in at_bats:
            is_out = re.search(r'Result: (Flyout|Groundout|Pop out)', at_bat_log)
            is_error = "An error by" in at_bat_log
            if is_out and is_error:
                self.fail("Incorrectly logged an out and an error in the same at-bat.")

    def test_velocity_regularity(self):
        """
        Analyst Concern: Fastballs clustered at neat integers.
        """
        log = self._run_sim_and_get_log()
        velocities = re.findall(r'\((\d{2,3}(?:\.\d)?) mph\)', log)
        has_float_velocities = any('.' in v for v in velocities)
        self.assertTrue(has_float_velocities,
                        "Pitch velocities are too regular and only use integers.")

if __name__ == '__main__':
    unittest.main()