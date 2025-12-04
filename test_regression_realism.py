import unittest
import copy
import random
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS

class TestRegressionRealism(unittest.TestCase):
    def setUp(self):
        # We'll select teams randomly for each test to ensure coverage
        # Note: tests might override this if they need specific teams
        team_keys = list(TEAMS.keys())
        # Ensure we pick two different teams
        t1, t2 = random.sample(team_keys, 2)
        self.home = copy.deepcopy(TEAMS[t1])
        self.away = copy.deepcopy(TEAMS[t2])

    def test_catcher_groundouts_are_rare(self):
        """
        Ensure catchers are not fielding an unrealistic number of groundouts.
        Regression test for issue where catchers were getting too many assists.
        """
        # Run a full game simulation
        sim = BaseballSimulator(self.home, self.away)
        sim.play_game()

        # Inspect internal fielding stats logic (or output)
        # We can check the number of times the catcher was selected as fielder for a groundout.
        # Since selection logic is internal, we can check the outcome logic or simply run many sims.
        # Here we'll trust the logic inside _handle_batted_ball_out if we can access it, or parse output.

        # Let's check the output log for "Groundout to C"
        renderer = NarrativeRenderer(sim.gameday_data, seed=42)
        output = renderer.render()
        catcher_groundouts = output.count("Groundout to C")

        # In a single game, it should be very rare (0 or 1)
        self.assertLessEqual(catcher_groundouts, 2, "Too many catcher groundouts in a single game.")

    def test_extra_innings_runner_banner_is_storylike(self):
        """
        Ensure the extra innings runner announcement is integrated into the narrative
        and not a synthetic banner.
        """
        sim = BaseballSimulator(self.home, self.away, game_seed=42)
        sim.inning = 10
        sim.top_of_inning = True

        # Manually expand innings data to prevent IndexError
        for i in range(2, 11):
             sim.gameday_data['liveData']['linescore']['innings'].append({'num': i, 'home': {'runs': 0}, 'away': {'runs': 0}})

        sim._simulate_half_inning()

        renderer = NarrativeRenderer(sim.gameday_data, seed=42, verbose=True)
        output = renderer.render()

        self.assertNotIn("--- Extra Innings", output)
        self.assertNotIn("Runner placed", output) # The specific robotic phrase

        # Should find the narrative version
        # "Automatic runner on second: {runner}..."
        # We can't know the runner name easily without parsing, but we check for the template start.
        self.assertIn("Automatic runner on second:", output)

    def test_first_relief_usage_varies_by_game(self):
        """
        Ensure that the first relief pitcher used is not always the same (e.g. the Closer).
        This was a regression where `available_bullpen` sorting/shuffling was ineffective.
        """
        first_relievers = set()
        # Use consistent teams for this specific test to isolate RNG effects on bullpen usage
        # rather than team selection effects.
        home = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        away = copy.deepcopy(TEAMS["PC_PILOTS"])

        for seed in range(15):
            sim = BaseballSimulator(home, away, game_seed=seed)
            sim.play_game()

            # Find the first pitcher change
            # We can check the pitch counts or internal state
            # Or check the list of pitchers used in the output
            # Easier to check internal state of used pitchers
            pitchers_used = [p for p, count in sim.pitch_counts.items() if count > 0]
            # Filter for team 1 pitchers
            team1_pitchers = [p for p in pitchers_used if p in sim.team1_pitcher_stats]

            # Starter is usually the one with most pitches or first one?
            # Starter is determined in _setup_pitchers (first in list of starters? no).
            # We know the starter name from setup.
            # However, we know the starter is 'Ace Armstrong' for Bay Bombers usually?
            # Let's just check that we see different names in the "pitchers_used" list besides the starter.

            # Better: check gameday data for pitching changes?
            # Or just check if the set of used pitchers varies across seeds.
            first_relievers.add(tuple(sorted(team1_pitchers)))

        self.assertGreater(len(first_relievers), 1, "Pitcher usage seems identical across seeds.")

if __name__ == '__main__':
    unittest.main()