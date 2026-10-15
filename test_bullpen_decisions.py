"""Pitcher hooks and running decisions calibrated against 136 MLB feeds."""
import collections
import statistics
import unittest
from unittest.mock import patch

from baseball import BaseballSimulator
from teams import TEAMS
from test_simulation_tells import baserunning_rate_counts, outs_recorded, pitcher_stints


def new_game(seed=0):
    return BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)


class TestPerformanceHooks(unittest.TestCase):
    def reliever_in_trouble(self, runs, faced=4, traffic=4, homers=1):
        game = new_game()
        game.inning, game.outs = 6, 1
        game._half_pitcher_entry = {}
        prefix, _, _, bullpen = game._pitching_side()
        game._bring_in(prefix, bullpen, mid_inning=True)
        name = game.team1_current_pitcher_name
        game.team2_score = runs
        game._batters_faced[name] = faced
        game._runs_allowed[name] = runs
        game._half_pitcher_traffic[name] = traffic
        game._half_pitcher_homers[name] = homers
        game.pitch_counts[name] = 18
        return game, name

    def test_a_grand_slam_can_end_a_relievers_inning_with_the_bases_empty(self):
        game, name = self.reliever_in_trouble(4)
        game._manage_pitching_change()
        self.assertNotEqual(game.team1_current_pitcher_name, name)
        self.assertTrue(game._entered_mid_inning[game.team1_current_pitcher_name])

    def test_trouble_is_tracked_through_the_actual_half_inning(self):
        game, name = self.reliever_in_trouble(0, faced=0, traffic=0, homers=0)
        game.inning = 1
        game.pitch_counts[name] = 0
        outcomes = iter(('Walk', 'Hit By Pitch', 'Walk', 'Home Run',
                         'Strikeout', 'Strikeout', 'Strikeout'))
        pitchers = []

        def at_bat(batter, pitcher):
            pitchers.append(pitcher['legal_name'])
            return next(outcomes), None, []

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat):
            game._simulate_half_inning()
        self.assertEqual(pitchers[:4], [name] * 4)
        self.assertNotEqual(pitchers[4], name)
        self.assertEqual(game._half_pitcher_traffic[name], 4)
        self.assertEqual(game._half_pitcher_homers[name], 1)

        with patch.object(game, '_simulate_at_bat', return_value=('Strikeout', None, [])):
            game._simulate_half_inning()
        self.assertEqual(game._half_pitcher_traffic, {})
        self.assertEqual(game._half_pitcher_homers, {})

    def test_repeated_homers_and_hits_get_a_hook_before_a_third_homer(self):
        game, name = self.reliever_in_trouble(2, homers=2)
        game.bases[1] = game.team2_lineup[0]['legal_name']
        game._manage_pitching_change()
        self.assertNotEqual(game.team1_current_pitcher_name, name)

    def test_a_homer_and_four_free_passes_do_not_wait_for_the_inning_break(self):
        game, name = self.reliever_in_trouble(2, faced=5, traffic=5)
        game.bases = [p['legal_name'] for p in game.team2_lineup[:3]]
        game._manage_pitching_change()
        self.assertNotEqual(game.team1_current_pitcher_name, name)

    def test_three_batter_minimum_still_applies_in_trouble(self):
        for faced in (1, 2):
            game, name = self.reliever_in_trouble(4, faced=faced)
            game._manage_pitching_change()
            self.assertEqual(game.team1_current_pitcher_name, name)
        game = new_game()
        name = game.team1_current_pitcher_name
        game._half_pitcher_entry = {name: 0}
        game._batters_faced[name] = 2
        game.pitch_counts[name] = 110
        game._manage_pitching_change()
        self.assertEqual(game.team1_current_pitcher_name, name)

    def test_starter_performance_changes_his_leash_with_the_same_pitch_budget(self):
        for runs, should_change in ((0, False), (4, True)):
            with self.subTest(runs=runs):
                game = new_game()
                game.inning = 6
                name = game.team1_current_pitcher_name
                game._half_pitcher_entry = {}
                game._pitch_budget[name] = 96
                game.pitch_counts[name] = 82
                game._batters_faced[name] = 18
                game._runs_allowed[name] = runs
                game.team2_score = runs
                game._manage_between_innings()
                self.assertEqual(game.team1_current_pitcher_name != name, should_change)

    def test_even_a_cruising_starter_still_has_a_pitch_limit(self):
        game = new_game()
        game.inning = 7
        name = game.team1_current_pitcher_name
        game._half_pitcher_entry = {}
        game._pitch_budget[name] = 96
        game.pitch_counts[name] = 100
        game._batters_faced[name] = 21
        game._manage_between_innings()
        self.assertNotEqual(game.team1_current_pitcher_name, name)


class TestSituationalSteals(unittest.TestCase):
    def attempt_rate(self, outs, margin=0, first_occupied=False, already_stole=False):
        game = new_game(512)
        game.inning = 6
        runner = next(p for p in game.team2_lineup if p['legal_name'] == 'Kevin Webb')
        game.outs = outs
        game.team2_score, game.team1_score = max(margin, 0), max(-margin, 0)
        game.bases = [game.team2_lineup[0]['legal_name'] if first_occupied else None,
                      runner['legal_name'], None]
        if already_stole:
            game._stolen_second_this_inning.add(runner['legal_name'])
        return sum(game._decide_steal_attempt(0, 0) == 3 for _ in range(6000)) / 6000

    def test_third_is_most_useful_with_one_out_but_two_out_attempts_still_exist(self):
        one_out = self.attempt_rate(1)
        self.assertLess(self.attempt_rate(0), one_out)
        two_out = self.attempt_rate(2)
        self.assertLess(two_out, one_out * 0.45)
        self.assertGreater(two_out, 0.005)

    def test_protect_the_runner_on_second_with_nobody_out_and_several_runs_needed(self):
        self.assertLess(self.attempt_rate(0, margin=-2), self.attempt_rate(0) / 5)

    def test_lone_steal_of_third_with_first_and_second_and_nobody_out_is_rare(self):
        self.assertLess(self.attempt_rate(0, first_occupied=True), self.attempt_rate(0) / 2)

    def test_stealing_second_is_not_an_automatic_green_light_for_third(self):
        self.assertLess(self.attempt_rate(1, already_stole=True), self.attempt_rate(1) * 0.8)


class TestBullpenAndRunningRates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts = collections.Counter()
        cls.starter_outs, cls.starter_pitches = [], []
        cls.relievers = []
        cls.scoreless_outs, cls.struggling_outs = [], []
        for seed in range(9400, 9600):
            game = new_game(seed)
            game.play_game()
            plays = game.gameday_data['liveData']['plays']['allPlays']
            for play in plays:
                ev = play['result']['eventType']
                cls.counts['pa'] += ev != 'caught_stealing'
                cls.counts['hbp'] += ev == 'hit_by_pitch'
            for top in (True, False):
                side, stints = pitcher_stints(plays, top)
                cls.relievers.append(len(stints) - 1)
                for n, (_, stint, clean) in enumerate(stints):
                    outs = outs_recorded(side, stint)
                    if n:
                        cls.counts['changes'] += 1
                        cls.counts['mid_changes'] += not clean
                        last_index, last_play = stint[-1]
                        finished = last_play['count']['outs'] >= 3 or last_index == len(side) - 1
                        cls.counts['short_stints'] += len(stint) < 3 and not finished
                    else:
                        name = stint[0][1]['matchup']['pitcher']['fullName']
                        cls.starter_outs.append(outs)
                        cls.starter_pitches.append(game.pitch_counts[name])
                        runs = game._runs_allowed[name]
                        if runs == 0:
                            cls.scoreless_outs.append(outs)
                        elif runs >= 4:
                            cls.struggling_outs.append(outs)

    def test_starters_have_a_wide_range_and_performance_matters(self):
        self.assertTrue(4.5 < statistics.mean(self.starter_outs) / 3 < 5.5)
        self.assertTrue(75 < statistics.mean(self.starter_pitches) < 92)
        self.assertGreater(statistics.pstdev(self.starter_pitches), 16)
        self.assertGreater(statistics.mean(self.scoreless_outs), statistics.mean(self.struggling_outs) + 1)

    def test_bullpen_usage_remains_varied_and_obeys_the_minimum(self):
        self.assertTrue(2.8 < statistics.mean(self.relievers) < 3.9)
        self.assertGreaterEqual(len(set(self.relievers)), 5)
        self.assertTrue(0.23 < self.counts['mid_changes'] / self.counts['changes'] < 0.43)
        self.assertEqual(self.counts['short_stints'], 0)

    def test_hit_batters_stay_near_one_percent_of_plate_appearances(self):
        self.assertTrue(0.0075 < self.counts['hbp'] / self.counts['pa'] < 0.0135)

    def test_steal_frequency_and_success_by_base(self):
        # Real: 1.34 attempts at second and 0.25 at third per game, with
        # caught-stealing rates of 14% and 15%, including pickoff CS.
        # Fifty attempts at third in 200 games let a few throws determine
        # the verdict. Keep the bands and use the larger calibration sample.
        counts = baserunning_rate_counts()
        self.assertTrue(0.95 < counts['2B'] / counts['games'] < 1.7, counts)
        self.assertTrue(0.12 < counts['3B'] / counts['games'] < 0.4, counts)
        self.assertTrue(0.07 < counts['cs_2B'] / counts['2B'] < 0.23, counts)
        self.assertTrue(0.04 < counts['cs_3B'] / counts['3B'] < 0.3, counts)


if __name__ == '__main__':
    unittest.main()
