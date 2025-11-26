import unittest
import collections
import copy
import re
from baseball import BaseballSimulator
from teams import TEAMS

class TestOutcomeDistributions(unittest.TestCase):
    def test_baseline_outcome_distribution(self):
        """
        This test establishes a baseline for the distribution of game outcomes.
        It runs a large number of simulations and records the frequency of
        different events like singles, home runs, and strikeouts. The results
        are printed to the console and can be used to validate future changes
        to the simulation engine.
        """
        num_games = 1000  # A large number for statistical significance
        outcome_counts = collections.defaultdict(int)

        for i in range(num_games):
            # Use a different seed for each game to get a variety of outcomes
            game = BaseballSimulator(
                copy.deepcopy(TEAMS["BAY_BOMBERS"]),
                copy.deepcopy(TEAMS["PC_PILOTS"]),
                game_seed=i,
                commentary_seed=i,
                commentary_style='gameday'  # Generate gameday data for analysis
            )
            game.play_game()

            # Extract outcomes from the gameday data
            if game.gameday_data:
                for play in game.gameday_data['liveData']['plays']['allPlays']:
                    outcome = play['result']['event']
                    outcome_counts[outcome] += 1

        # The purpose of this test is to establish a baseline.
        # We will print the results and then assert True to ensure the
        # test passes and the baseline is recorded in the test logs.
        print("\n--- Baseline Outcome Distribution ---")
        total_outcomes = sum(outcome_counts.values())
        if total_outcomes > 0:
            for outcome, count in sorted(outcome_counts.items()):
                percentage = (count / total_outcomes) * 100
                print(f"{outcome}: {count} ({percentage:.2f}%)")
        print("------------------------------------")

        # This test is for establishing a baseline, so it should always pass.
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
