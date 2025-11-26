import unittest
import copy
from collections import defaultdict
from baseball import BaseballSimulator
from teams import TEAMS

class TestOutcomeDistributions(unittest.TestCase):
    def test_baseline_outcome_distribution(self):
        """
        This test establishes a baseline for the distribution of game outcomes.
        It is not a pass/fail test in the traditional sense, but rather a tool
        for detecting significant changes in simulation behavior. If this test
        fails, it means the outcome distribution has changed, and the new
        distribution should be reviewed and potentially accepted as the new baseline.
        """
        outcomes = defaultdict(int)
        num_simulations = 100
        for i in range(num_simulations):
            game = BaseballSimulator(
                copy.deepcopy(TEAMS["BAY_BOMBERS"]),
                copy.deepcopy(TEAMS["PC_PILOTS"]),
                game_seed=i
            )
            gameday_data = game.play_game()
            for play in gameday_data['liveData']['plays']['allPlays']:
                outcomes[play['result']['event']] += 1

        # This expected distribution is based on a prior run of the simulation.
        # If the simulation logic changes, this distribution may need to be updated.
        expected_distribution = {
            'Groundout': 412,
            'Strikeout': 421,
            'Flyout': 238,
            'Walk': 156,
            'Single': 222,
            'Double': 77,
            'Home Run': 43,
            'Pop Out': 30,
            'Lineout': 26,
            'Triple': 4,
            'Double Play': 37,
            'Field Error': 18,
            'Hit By Pitch': 8,
            'Sac Fly': 6,
            'Forceout': 1,
            'Caught Stealing': 1,
        }

        # The test will fail if the new distribution deviates significantly.
        for outcome, count in expected_distribution.items():
            self.assertAlmostEqual(
                outcomes[outcome],
                count,
                delta=count * 0.5, # Allow for a 50% tolerance
                msg=f"Outcome '{outcome}' count {outcomes[outcome]} differs significantly from expected {count}"
            )

if __name__ == '__main__':
    unittest.main()
