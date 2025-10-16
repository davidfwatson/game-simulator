import unittest
import random
import io
import re
import copy
from contextlib import redirect_stdout
from baseball import BaseballSimulator
from teams import TEAMS

class TestAnalystConcerns(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        # A fixed seed ensures that the tests are deterministic.
        random.seed(42)

    def _run_sim_and_get_log(self, num_games=1, commentary_style='narrative'):
        """A helper method to run the simulation and capture its output."""
        full_log = []
        for i in range(num_games):
            random.seed(i)
            # We re-initialize the game each time to reset the state
            game = BaseballSimulator(
                copy.deepcopy(TEAMS["BAY_BOMBERS"]),
                copy.deepcopy(TEAMS["PC_PILOTS"]),
                commentary_style=commentary_style
            )
            game.play_game()
            full_log.extend(game.output_lines)
        return "\n".join(full_log)

    def test_mechanical_phrasing_of_pitches(self):
        """
        Analyst Concern: Nearly every pitch says “in the strike zone” (or simple “inside/high/low”)
        with no granular location or Statcast-style variation.

        Test: This test runs a simulation and checks for a wider variety of pitch location descriptions.
        It will fail if only the basic, mechanical descriptions are found.
        """
        log = self._run_sim_and_get_log()

        # This pattern finds pitch descriptions (e.g., "called a strike", "misses low").
        # It's broader to accommodate the new, more varied phrasing.
        location_phrases = re.findall(r'  (?:Foul, )?(.*?)\. \d+-\d+\.', log)

        # Basic phrases that indicate mechanical, less descriptive commentary.
        basic_phrases = {"Ball", "Called Strike", "Swinging Strike"}

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

        # Regexes now look for the correct text descriptions instead of abbreviations.
        popouts = len(re.findall(r'pops out to (?:back to the mound|in front of the plate|first|second|third|short)', log, re.IGNORECASE))
        flyouts = len(re.findall(r'(?:flies out|lines out) to (?:left|center|right)', log, re.IGNORECASE))

        # Count walks by looking for the explicit "draws a walk" phrase.
        walks = log.count("draws a walk")

        # In real baseball, outfield flyouts are significantly more common than infield popouts.
        self.assertTrue(flyouts > popouts * 1.5,
                        f"Unrealistic outcome distribution: {popouts} popouts vs. {flyouts} flyouts. "
                        "Expected more flyouts.")

        # A typical game has several walks. Over 100 games, we expect a healthy number.
        self.assertTrue(walks > 100, # Average of 1+ walks per game
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
        # Split the log by at-bats to isolate each play.
        at_bats = log.split("steps to the plate.")[1:]

        for at_bat_log in at_bats:
            # The new commentary correctly suppresses the 'out' description on an error.
            # So, we check if an out verb (like "grounds out") appears alongside an error message.
            has_out_verb = re.search(r'(grounds out|flies out|pops out)', at_bat_log, re.IGNORECASE)
            has_error_message = "error on" in at_bat_log.lower()

            if has_out_verb and has_error_message:
                self.fail("Logged an out verb and an error in the same at-bat, which is contradictory."
                          f"\n---LOG---\n...steps to the plate.{at_bat_log}\n----------")

    def test_velocity_regularity(self):
        """
        Analyst Concern: Fastballs clustered at neat integers (94–97) and secondaries at
        tidy bands (78–84, 86–90) with minimal drift.

        Test: This test checks if pitch velocities are all whole numbers.
        It will fail if no floating-point velocities (e.g., 94.3 mph) are found,
        indicating that the velocities are too regular and lack human-like variance.
        """
        log = self._run_sim_and_get_log(commentary_style='statcast') # Statcast has reliable velocity output

        # This pattern finds all velocities from the statcast output.
        velocities = re.findall(r'(\d{2,3}\.\d) mph', log)

        # We expect to find at least one floating point velocity.
        has_float_velocities = len(velocities) > 0

        self.assertTrue(has_float_velocities,
                        "Pitch velocities are too regular and only use integers. "
                        "Expected floating-point values for more realism.")

if __name__ == '__main__':
    unittest.main()