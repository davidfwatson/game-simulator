import unittest
import copy
import math
from collections import defaultdict
from baseball import BaseballSimulator
from teams import TEAMS

class TestOutcomeDistributions(unittest.TestCase):
    def test_baseline_outcome_distribution(self):
        """
        Validates simulation against 2024 MLB League Average statistics for 100 games.
        Uses a 4-sigma tolerance (approx 99.99% confidence interval) to prevent flaky tests
        while catching major logic regressions.
        """
        outcomes = defaultdict(int)
        num_simulations = 100

        # Run 100 games
        for i in range(num_simulations):
            game = BaseballSimulator(
                copy.deepcopy(TEAMS["BAY_BOMBERS"]),
                copy.deepcopy(TEAMS["PC_PILOTS"]),
                game_seed=i
            )
            game.play_game()
            gameday_data = game.gameday_data
            for play in gameday_data['liveData']['plays']['allPlays']:
                # Ensure we only count the final event of the play
                if 'event' in play['result']:
                    outcomes[play['result']['event']] += 1

                # Count events within the play (like Stolen Bases)
                if 'playEvents' in play:
                    for event in play['playEvents']:
                        if 'details' in event and 'eventType' in event['details']:
                            etype = event['details']['eventType']
                            if etype == 'stolen_base':
                                outcomes['Stolen Base'] += 1
                            # Caught stealing is often the result of the play, but check events just in case?
                            # Usually CS ends the inning or is an out, recorded in result.
                            # But if it's not the last out?
                            # The simulator returns "Caught Stealing" as main outcome if it's the 3rd out.
                            # If it's not the 3rd out, it might just be an event.
                            elif etype == 'caught_stealing' and play['result']['event'] != 'Caught Stealing':
                                outcomes['Caught Stealing'] += 1

        # Baseline: 2024 MLB Stats scaled to 100 games (approx 7,500 Plate Appearances)
        expected_distribution = {
            'Strikeout': 1690,
            'Groundout': 1450,
            'Flyout': 1150,
            'Single': 1060,
            'Walk': 630,
            'Lineout': 350,   # Lower than your previous 790; Line drives are usually hits!
            'Double': 320,
            'Home Run': 230,
            'Pop Out': 180,
            'Stolen Base': 150, # Added this as it's a key stat now
            'Double Play': 145,
            'Field Error': 115,
            'Hit By Pitch': 85,
            'Sac Fly': 50,
            'Forceout': 45,   # Batter reaches on Fielder's Choice
            'Caught Stealing': 40,
            'Triple': 27,
        }

        # Overrides for current simulation inaccuracies
        # All overrides removed as simulation now matches MLB distributions well!
        delta_overrides = {}

        print("\n--- Simulation Outcome Report ---")
        print(f"{'Outcome':<20} | {'Actual':<10} | {'Expected':<10} | {'Delta Limit'}")
        print("-" * 60)

        for outcome, expected_count in expected_distribution.items():
            actual_count = outcomes[outcome]

            # Calculate 4-sigma variance (approx 99.99% confidence for Poisson distribution)
            # For very small counts, we set a minimum floor to avoid brittle failures.
            sigma = math.sqrt(expected_count)
            delta_limit = max(int(4 * sigma), 15)

            if outcome in delta_overrides:
                delta_limit = delta_overrides[outcome]

            print(f"{outcome:<20} | {actual_count:<10} | {expected_count:<10} | +/- {delta_limit}")

            self.assertAlmostEqual(
                actual_count,
                expected_count,
                delta=delta_limit,
                msg=f"Outcome '{outcome}' count {actual_count} is outside realistic MLB bounds ({expected_count} +/- {delta_limit})"
            )

if __name__ == '__main__':
    unittest.main()
