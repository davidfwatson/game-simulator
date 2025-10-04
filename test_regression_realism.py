import io
import random
import unittest
from contextlib import redirect_stdout

from baseball import BaseballSimulator
from teams import TEAMS


class TestRegressionRealism(unittest.TestCase):
    def setUp(self):
        self.home = TEAMS["BAY_BOMBERS"]
        self.away = TEAMS["PC_PILOTS"]

    def test_catcher_groundouts_are_rare(self):
        random.seed(123)
        sim = BaseballSimulator(self.home, self.away, verbose_phrasing=False)
        sim.top_of_inning = True

        catcher_groundouts = 0
        total_groundouts = 0

        for _ in range(5000):
            sim.outs = 0
            sim.bases = [None, None, None]
            desc, _, was_error = sim._handle_batted_ball_out("Groundout", sim.team2_lineup[0])
            if was_error:
                continue
            total_groundouts += 1
            if "2-3" in desc:
                catcher_groundouts += 1

        self.assertGreater(total_groundouts, 0)
        rate = catcher_groundouts / total_groundouts
        self.assertLess(
            rate,
            0.05,
            f"Catchers handled {rate:.3%} of routine grounders; expected this to be a rare event."
        )

    def test_extra_innings_runner_banner_is_storylike(self):
        random.seed(99)
        sim = BaseballSimulator(self.home, self.away)
        sim.inning = 10
        sim.top_of_inning = False
        sim.team1_batter_idx = 3

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            sim._simulate_half_inning()
        log = buffer.getvalue()

        self.assertNotIn("--- Extra Innings", log)
        self.assertNotIn("placed on second base.", log)

    def test_first_relief_usage_varies_by_game(self):
        relievers_used = []
        for seed in range(5):
            random.seed(seed)
            sim = BaseballSimulator(self.home, self.away)
            starter = sim.team1_current_pitcher_name
            sim.pitch_counts[starter] = sim.team1_pitcher_stats[starter]['stamina'] + 40
            sim.top_of_inning = True
            sim._manage_pitching_change()
            relievers_used.append(sim.team1_current_pitcher_name)
        self.assertGreater(
            len(set(relievers_used)),
            1,
            "Bullpen usage is identical across games; expected different first relievers."
        )

    def test_play_by_play_avoids_engine_tells(self):
        random.seed(2024)
        sim = BaseballSimulator(self.home, self.away)
        pitcher = sim.team2_pitcher_stats[sim.team2_current_pitcher_name]
        batter = sim.team1_lineup[0]

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            sim._simulate_at_bat(batter, pitcher)
        log = buffer.getvalue()

        self.assertNotIn("In play ->", log)


if __name__ == "__main__":
    unittest.main()
