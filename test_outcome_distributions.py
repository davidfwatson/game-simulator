import unittest
import copy
import math
from collections import defaultdict
from baseball import BaseballSimulator
from teams import TEAMS

class TestOutcomeDistributions(unittest.TestCase):
    def test_baseline_outcome_distribution(self):
        """
        Validates 100 games against 136 complete real 2026 StatsAPI feeds.
        Uses a four-sigma Poisson difference, including sampling uncertainty
        in both the real feeds and simulations, to catch major regressions.
        """
        outcomes = defaultdict(int)
        plate_appearances = 0
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
                    plate_appearances += play['about'].get('isComplete') is not False

                # Count events within the play (like Stolen Bases)
                if 'playEvents' in play:
                    for event in play['playEvents']:
                        if 'details' in event and 'eventType' in event['details']:
                            etype = event['details']['eventType']
                            if etype == 'stolen_base':
                                outcomes['Stolen Base'] += 1
                            # Caught stealing is often the result of the play, but check events just in case?
                            # Usually CS ends the inning or is an out, recorded in result.
                            # But if it's not the 3rd out.
                            elif etype == 'caught_stealing' and play['result']['event'] != 'Caught Stealing':
                                outcomes['Caught Stealing'] += 1

        # Observed counts in 10,309 completed PA in the real feeds. Scale by
        # actual PA rather than assuming every 100 games have 7,500 PA; an
        # inning-ending baserunning out is not a completed plate appearance.
        # Normalize feed labels to the simulator's result names: all walks
        # include intentional walks; Double Play includes Grounded Into DP.
        real_counts = {
            'Strikeout': 2248,
            'Groundout': 1727,
            'Flyout': 1313,
            'Single': 1512,
            'Walk': 919,
            'Lineout': 571,
            'Double': 395,
            'Home Run': 310,
            'Pop Out': 509,
            'Double Play': 212,
            'Field Error': 62,   # batter reached on error, not all charged errors
            'Hit By Pitch': 113,
            'Sac Fly': 78,
            'Forceout': 185,
            'Triple': 41,
        }
        expected_distribution = {event: count * plate_appearances / 10309
                                 for event, count in real_counts.items()}
        # Runner events have opportunities within a PA, so compare their
        # game rates. Include pickoff-caught-stealing actions in the real CS.
        expected_distribution.update({'Stolen Base': 186 * num_simulations / 136,
                                      'Caught Stealing': 30 * num_simulations / 136,
                                      'Plate Appearance': 10309 * num_simulations / 136})
        outcomes['Plate Appearance'] = plate_appearances

        print("\n--- Simulation Outcome Report ---")
        print(f"{plate_appearances} completed plate appearances in {num_simulations} games")
        print(f"{'Outcome':<20} | {'Actual':<10} | {'Expected':<10} | {'Delta Limit'}")
        print("-" * 60)

        for outcome, expected_count in expected_distribution.items():
            actual_count = outcomes[outcome]

            # Var(sim - scale * real) = expected * (1 + scale). The real
            # baseline is a 136-game sample, not a known population mean.
            # Keep the original four-sigma rule and small-count floor.
            scale = plate_appearances / 10309 if outcome in real_counts else num_simulations / 136
            sigma = math.sqrt(expected_count * (1 + scale))
            delta_limit = max(int(4 * sigma), 15)

            print(f"{outcome:<20} | {actual_count:<10} | {expected_count:<10.1f} | +/- {delta_limit}")

            with self.subTest(outcome=outcome):
                self.assertAlmostEqual(
                    actual_count,
                    expected_count,
                    delta=delta_limit,
                    msg=f"Outcome '{outcome}' count {actual_count} is outside realistic MLB bounds ({expected_count:.1f} +/- {delta_limit})"
                )

if __name__ == '__main__':
    unittest.main()
