"""Count situations and outing variation, from 136 complete real 2026 feeds."""
import collections
import statistics
import unittest

from baseball import BaseballSimulator
from teams import TEAMS


NON_PA = ('pickoff', 'caught_stealing', 'stolen_base', 'other_out', 'runner_out')


class TestCountShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reached, cls.first = collections.Counter(), collections.Counter()
        cls.full_halves, cls.full_stretches, cls.pitcher_games = [], [], []
        cls.pa = 0
        cls.role_pa, cls.role_walks = collections.Counter(), collections.Counter()
        for seed in range(23000, 23240):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
            game.play_game()
            starters = {box['pitchers'][0] for box in game.gameday_data['liveData']['boxscore']['teams'].values()}
            halves, pitchers = collections.defaultdict(list), collections.defaultdict(collections.Counter)
            for play in game.gameday_data['liveData']['plays']['allPlays']:
                result = play['result']['eventType']
                if result.startswith(NON_PA):
                    continue
                events = [e for e in play['playEvents'] if e.get('isPitch')]
                reached = {(e['count']['balls'], e['count']['strikes']) for e in events}
                cls.reached.update(reached)
                cls.pa += 1
                if events:
                    cls.first[events[0]['details']['code']] += 1
                half = play['about']['inning'], play['about']['isTopInning']
                halves[half].append((3, 2) in reached)
                pid = play['matchup']['pitcher']['id']
                role = 'starter' if pid in starters else 'reliever'
                walk = result == 'walk'
                cls.role_pa[role] += 1
                cls.role_walks[role] += walk
                pitchers[pid].update(pa=1, walks=walk, pitches=len(events))
            cls.full_halves.extend(sum(full) for (inning, _), full in halves.items() if inning <= 9)
            for start in range(1, 8):
                keys = [(inning, top) for inning in range(start, start + 3) for top in (True, False)]
                if all(key in halves for key in keys):
                    cls.full_stretches.append(sum(sum(halves[key]) for key in keys))
            cls.pitcher_games.extend(p for pid, p in pitchers.items() if pid in starters and p['pa'] >= 12)

    def test_each_count_is_reached_at_a_realistic_rate(self):
        # Shares of PA in the real feeds, including 14.02% full counts.
        real = {(0, 1): 0.498, (0, 2): 0.216, (1, 0): 0.378, (1, 1): 0.379,
                (1, 2): 0.290, (2, 0): 0.125, (2, 1): 0.201, (2, 2): 0.239,
                (3, 0): 0.0384, (3, 1): 0.0845, (3, 2): 0.1402}
        for count, target in real.items():
            with self.subTest(count=count):
                self.assertAlmostEqual(self.reached[count] / self.pa, target, delta=0.016)

    def test_full_counts_can_cluster_without_dominating_the_excerpt(self):
        # Real: 0.598 per half (sd 0.763), 3.55 per three innings (sd 1.86).
        self.assertTrue(0.52 < statistics.mean(self.full_halves) < 0.68)
        self.assertTrue(0.68 < statistics.pstdev(self.full_halves) < 0.86)
        self.assertTrue(3.15 < statistics.mean(self.full_stretches) < 4.0)
        self.assertTrue(1.6 < statistics.pstdev(self.full_stretches) < 2.15)
        self.assertLess(sum(n >= 9 for n in self.full_stretches) / len(self.full_stretches), 0.025)

    def test_first_pitches_are_not_excessively_put_in_play(self):
        # Real: ball 37.8%, called strike 29.5%, miss 8.0%, foul 12.3%, fair 11.8%.
        for code, target in (('B', 0.378), ('C', 0.295), ('S', 0.080), ('F', 0.123), ('X', 0.118)):
            with self.subTest(outcome=code):
                self.assertAlmostEqual(self.first[code] / self.pa, target, delta=0.016)

    def test_starters_are_not_consistently_wilder_than_the_bullpen(self):
        # Real: starters walk 8.28% of batters, relievers 9.70%.
        starter = self.role_walks['starter'] / self.role_pa['starter']
        reliever = self.role_walks['reliever'] / self.role_pa['reliever']
        self.assertTrue(0.065 < starter < 0.105, starter)
        self.assertTrue(0.075 < reliever < 0.12, reliever)
        self.assertLess(starter, reliever + 0.01)

    def test_pitcher_outings_keep_good_and_bad_control_days(self):
        # Real starters facing 12+: BB% variance .00457, pitches/PA variance .190.
        walk_rates = [p['walks'] / p['pa'] for p in self.pitcher_games]
        pitch_rates = [p['pitches'] / p['pa'] for p in self.pitcher_games]
        self.assertTrue(0.0032 < statistics.pvariance(walk_rates) < 0.0065)
        self.assertTrue(0.14 < statistics.pvariance(pitch_rates) < 0.25)
        no_walks = sum(p['walks'] == 0 for p in self.pitcher_games) / len(self.pitcher_games)
        self.assertTrue(0.10 < no_walks < 0.26, no_walks)


class TestThreeOhGreenLight(unittest.TestCase):
    def setUp(self):
        self.game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=71)
        self.batter = self.game.team2_lineup[3]

    def swings(self, lead=0, inning=4, runners=False, top=True, batter=None, zone=5, kind='four-seam fastball'):
        game = self.game
        game.inning, game.top_of_inning = inning, top
        game.team1_score, game.team2_score = (10, 10 + lead) if top else (10 + lead, 10)
        game.bases = ['Runner' if runners else None, None, None]
        game.game_rng.seed(312)
        return sum(game._simulate_bat_swing(batter or self.batter, zone <= 9, 3, 0, zone, kind)
                   for _ in range(10000)) / 10000

    def test_three_oh_takes_account_of_the_batting_teams_score(self):
        for top in (True, False):
            close = self.swings(top=top)
            for lead in (-4, 4):
                with self.subTest(top=top, lead=lead):
                    early = self.swings(lead=lead, top=top)
                    late = self.swings(lead=lead, inning=8, top=top)
                    self.assertLess(early, close * 0.4)
                    self.assertLess(late, early * 0.75)
                    self.assertGreater(late, 0)

    def test_hitters_can_still_attack_a_pitch_they_can_drive(self):
        fastball = self.swings()
        self.assertGreater(fastball, 0.15)
        self.assertGreater(self.swings(runners=True), fastball)
        self.assertGreater(fastball, self.swings(batter=self.game.team2_lineup[1]) * 2)
        self.assertLess(self.swings(zone=12), 0.02)
        self.assertLess(self.swings(kind='curveball'), fastball * 0.6)

    def test_other_counts_do_not_get_the_three_oh_take_sign(self):
        rates = []
        for lead in (-4, 0, 4):
            self.game.team1_score, self.game.team2_score = 10, 10 + lead
            self.game.game_rng.seed(313)
            rates.append(sum(self.game._simulate_bat_swing(self.batter, True, 3, 1, 5, 'four-seam fastball')
                             for _ in range(1000)))
        self.assertEqual(len(set(rates)), 1)


class TestPitcherCommand(unittest.TestCase):
    def test_control_changes_between_games_and_persists_within_an_outing(self):
        rates = []
        pitcher = next(p for p in TEAMS['BAY_BOMBERS']['players'] if p.get('type') == 'Starter')
        original_control = pitcher['control']
        for seed in range(64):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
            today = game.team1_pitcher_stats[pitcher['legal_name']]
            # Use the same pitch draws each day to isolate persistent command
            # from the ordinary sampling noise of individual pitches.
            game.game_rng.seed(314)
            first = [game._simulate_pitch_trajectory(today)[0] for _ in range(1000)]
            rates.append(sum(first) / len(first))
            game.inning = 7
            game.game_rng.seed(314)
            self.assertEqual(first, [game._simulate_pitch_trajectory(today)[0] for _ in range(1000)])
        self.assertTrue(0.03 < statistics.pstdev(rates) < 0.08)
        self.assertEqual(pitcher['control'], original_control)


if __name__ == '__main__':
    unittest.main()
