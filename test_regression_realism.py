import io
import random
import unittest
from contextlib import redirect_stdout

from baseball import BaseballSimulator
from gameday_converter import GamedayConverter
from teams import TEAMS


class TestRegressionRealism(unittest.TestCase):
    def setUp(self):
        self.home = TEAMS["BAY_BOMBERS"]
        self.away = TEAMS["PC_PILOTS"]

    def test_catcher_groundouts_are_rare(self):
        random.seed(123)
        sim = BaseballSimulator(self.home, self.away)
        sim.top_of_inning = True

        catcher_groundouts = 0
        total_groundouts = 0

        for _ in range(5000):
            sim.outs = 0
            sim.bases = [None, None, None]
            _, _, was_error, _, _, _, _, desc = sim._handle_batted_ball_out("Groundout", sim.team2_lineup[0])
            if was_error:
                continue
            total_groundouts += 1
            if "Groundout to Catcher" in desc:
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

        gameday_data = sim.play_game()
        converter = GamedayConverter(gameday_data)
        log = converter.convert()

        self.assertNotIn("--- Extra Innings", log)
        self.assertNotIn("placed on second base.", log)

    def test_first_relief_usage_varies_by_game(self):
        relievers_used = []
        for seed in range(5):
            sim = BaseballSimulator(self.home, self.away, game_seed=seed, commentary_seed=seed)
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
        gameday_data = sim.play_game()
        converter = GamedayConverter(gameday_data)
        log = converter.convert()

        self.assertNotIn("In play ->", log)


if __name__ == "__main__":
    unittest.main()
