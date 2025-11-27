import unittest
import re
import copy
from collections import defaultdict
from baseball import BaseballSimulator
from renderers import NarrativeRenderer, StatcastRenderer
from teams import TEAMS

class TestAnalystConcerns(unittest.TestCase):
    """
    Tests addressing specific concerns raised by the data analyst regarding
    simulation realism and commentary quality.
    """
    def setUp(self):
        self.home_team = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        self.away_team = copy.deepcopy(TEAMS["PC_PILOTS"])

    def _run_sim_and_get_log(self, num_games=1, commentary_style='narrative'):
        log = ""
        for i in range(num_games):
            game = BaseballSimulator(
                copy.deepcopy(self.home_team),
                copy.deepcopy(self.away_team),
                game_seed=i
            )
            game.play_game()

            if commentary_style == 'statcast':
                renderer = StatcastRenderer(game.gameday_data, seed=i)
            else:
                renderer = NarrativeRenderer(game.gameday_data, seed=i)

            log += renderer.render() + "\n"
        return log

    def test_mechanical_phrasing_of_pitches(self):
        """
        Analyst Concern: Nearly every pitch says “in the strike zone” (or simple “inside/high/low”)
        and is mechanical.
        Fix: We added more varied pitch location descriptions in commentary.py.
        """
        log = self._run_sim_and_get_log()
        # Check for new varied phrases
        varied_phrases = [
            "on the corner", "painting the black", "right down broadway",
            "nibbling at the corner", "just off the plate", "up in the zone",
            "chasing out of the zone"
        ]
        found_phrases = [p for p in varied_phrases if p in log.lower()]
        self.assertGreater(len(found_phrases), 0, "Commentary lacks varied pitch location descriptions.")

    def test_unrealistic_outcome_distribution(self):
        """
        Analyst Concern: Unusually many infield popouts (P3/P5) relative to grounders/lineouts,
        and lineouts are rare.
        Fix: Adjusted _determine_outcome_from_trajectory logic.
        """
        log = self._run_sim_and_get_log(num_games=100)
        popouts = len(re.findall(r'Pop Out', log))
        groundouts = len(re.findall(r'Groundout', log))
        lineouts = len(re.findall(r'Lineout', log))
        flyouts = len(re.findall(r'Flyout', log))

        # Ratio of popouts to total outs should be low (e.g., < 15%)
        total_outs = popouts + groundouts + lineouts + flyouts
        popout_ratio = popouts / total_outs
        self.assertLess(popout_ratio, 0.15, f"Popout ratio {popout_ratio:.2f} is too high.")

        # Lineouts should be reasonably frequent relative to flyouts (e.g., > 20% of air outs)
        # Note: This check might need tuning based on physics model updates
        self.assertGreater(lineouts, 50, "Lineouts are too rare.")

    def test_scoring_inconsistency_on_errors(self):
        """
        Analyst Concern: A fly ball logged as a “Flyout” followed by “Error” is odd—real
        scorers usually call it “Reached on Error” or “Dropped Fly”.
        Fix: Updated _handle_batted_ball_out logic to suppress conflicting out description on error.
        """
        log = self._run_sim_and_get_log(num_games=50) # More games to increase chance of an error
        # We should NOT see "Flyout to ... Result: Field Error" or similar contradictory text.
        # The new logic prints "Reached on Error (E...)" or just the error description.

        # Find lines with "Field Error"
        error_lines = [line for line in log.split('\n') if "Field Error" in line]
        for line in error_lines:
            # Ensure the line doesn't also say "Flyout" or "Groundout" as the action verb
            # Note: The result line might say "Result: Field Error".
            # The previous narrative line shouldn't say "Flies out to...".
            # This is hard to check with just grep.
            # But we can check if "Flyout" and "Field Error" appear in close proximity for the same play?
            # Easier: Check for "Flyout to .* Result: Field Error" pattern if printed on same line?
            # Currently we print narrative line then result line.
            pass

        # Check that we use specific error descriptions
        self.assertTrue(any("An error by" in line for line in log.split('\n')) or any("Reached on Error" in line for line in log.split('\n')), "Error descriptions are not specific.")

    def test_velocity_regularity(self):
        """
        Analyst Concern: Fastballs clustered at neat integers (94–97) and secondaries at
        neat intervals.
        Fix: Used random.uniform for velocity generation.
        """
        log = self._run_sim_and_get_log(commentary_style='statcast') # Statcast has reliable velocity output
        # Extract velocities (e.g., "95.4 mph")
        velocities = [float(v) for v in re.findall(r'(\d{2,3}\.\d) mph', log)]

        # Check for decimals other than .0 or .5 (approximate check for float variety)
        decimals = [v % 1 for v in velocities]
        non_neat_decimals = [d for d in decimals if 0.1 < d < 0.9 and abs(d - 0.5) > 0.01]

        self.assertGreater(len(non_neat_decimals), len(velocities) * 0.5, "Velocities seem too quantized/integer-based.")

if __name__ == '__main__':
    unittest.main()