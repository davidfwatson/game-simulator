"""Managerial decisions and the situations that call for them."""
import collections
import random
import unittest
from unittest.mock import patch

from baseball import BaseballSimulator
from teams import TEAMS


def new_game(seed=1):
    return BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)


class TestStrategyRandomness(unittest.TestCase):
    def test_setup_and_managerial_choices_leave_pitch_randomness_alone(self):
        game = new_game()
        state = random.Random(1).getstate()
        self.assertEqual(game.game_rng.getstate(), state)
        game.inning = 8
        game.bases[0] = game.team2_lineup[0]['legal_name']
        pitcher = game._pitching_side()[2]
        game._bunt_plan(game.team2_lineup[8])
        game._decide_steal_attempt(0, 1)
        game._decide_pickoff_throw(0)
        game._manage_offensive_substitutions(8, pitcher)
        game._manage_defensive_substitutions()
        game._half_pitcher_entry = {}
        game._batters_faced[pitcher['legal_name']] = 20
        game._manage_pitching_change()
        game._manage_between_innings()
        self.assertEqual(game.game_rng.getstate(), state)

    def test_a_safe_pickoff_throw_does_not_reshuffle_the_next_pitch(self):
        game = new_game()
        game.bases[0] = game.team2_lineup[0]['legal_name']
        pitcher = game._pitching_side()[2]
        state = game.game_rng.getstate()
        events = []
        with patch.object(game.strategy_rng, 'random', return_value=0.9):
            game._record_pickoff_throw(events, 0, 0, pitcher)
        self.assertEqual(game.game_rng.getstate(), state)
        self.assertEqual(game.outs, 0)
        self.assertEqual(len(events), 1)

    def test_strategy_and_texture_streams_are_seeded_independently(self):
        game, replay, other = new_game(), new_game(), new_game(2)
        self.assertEqual(game.strategy_rng.getstate(), replay.strategy_rng.getstate())
        self.assertEqual(game.texture_rng.getstate(), replay.texture_rng.getstate())
        self.assertNotEqual(game.strategy_rng.getstate(), other.strategy_rng.getstate())
        game.strategy_rng.random()
        game.texture_rng.random()
        self.assertEqual(game.game_rng.getstate(), replay.game_rng.getstate())


class TestBuntSituations(unittest.TestCase):
    def setUp(self):
        self.game = new_game()
        self.game.inning = 6
        self.batter = self.game.team2_lineup[8]

    def plan(self, outs, occupied, inning=6, margin=0):
        game = self.game
        game.outs, game.inning = outs, inning
        game.team1_score, game.team2_score = max(0, -margin), max(0, margin)
        game.bases = [game.team2_lineup[i]['legal_name'] if str(i+1) in occupied else None
                      for i in range(3)]
        with patch.object(game.strategy_rng, 'random', return_value=0):
            return game._bunt_plan(self.batter)

    def test_no_two_out_bunt_with_runners_or_one_out_sacrifice_of_two_runners(self):
        for occupied in ('1', '2', '12', '13', '23', '123'):
            self.assertEqual(self.plan(2, occupied), (False, False))
        self.assertEqual(self.plan(1, '12'), (False, False))

    def test_sacrifice_of_second_is_saved_for_later_in_a_close_game(self):
        self.assertEqual(self.plan(0, '2', inning=3), (False, False))
        self.assertEqual(self.plan(0, '2', inning=8), (True, True))
        self.assertEqual(self.plan(0, '2', inning=8, margin=-3), (False, False))

    def test_do_not_sacrifice_when_two_runs_are_needed_late(self):
        for outs in (0, 1):
            self.assertEqual(self.plan(outs, '1', inning=8, margin=-2), (False, False))

    def test_pinch_hitter_does_not_bunt_down_two_in_the_eighth(self):
        self.batter = self.game.team2_bench[0]
        self.game._substitute('team2', 8, self.batter, 'PH')
        self.assertEqual(self.plan(1, '1', inning=8, margin=-2), (False, False))

    def test_fast_hitter_can_bunt_for_a_hit_with_two_outs_and_nobody_on(self):
        self.batter = self.game.team2_lineup[1]
        self.assertEqual(self.plan(2, ''), (True, False))
        self.batter = self.game.team2_lineup[3]
        self.assertEqual(self.plan(2, ''), (False, False))


class TestPickoffSituations(unittest.TestCase):
    def rate(self, runner_slot=1, occupied='1', lead=0, throws=0):
        game = new_game(71)
        game.team1_score, game.team2_score = max(0, lead), max(0, -lead)
        game.bases = [game.team2_lineup[runner_slot]['legal_name'] if i == 0 else
                      game.team2_lineup[i+1]['legal_name'] if str(i+1) in occupied else None
                      for i in range(3)]
        return sum(game._decide_pickoff_throw(throws) is not None for _ in range(6000)) / 6000

    def test_pickoffs_follow_steal_threat_and_the_open_base(self):
        open_base = self.rate()
        self.assertGreater(open_base, self.rate(runner_slot=3) * 8)
        self.assertGreater(open_base, self.rate(occupied='12') * 4)
        self.assertGreater(open_base, self.rate(lead=5) * 1.4)
        self.assertEqual(self.rate(occupied='123'), 0)
        self.assertEqual(self.rate(lead=8), 0)
        self.assertEqual(self.rate(throws=2), 0)


class TestMoundVisitSituations(unittest.TestCase):
    def setUp(self):
        self.game = new_game()
        self.pitcher = self.game._pitching_side()[2]
        self.name = self.pitcher['legal_name']
        self.game._half_pitcher_entry = {}

    def rate(self, inning, pitches, runners, traffic=0, last_faced=-100):
        game = self.game
        game.inning = inning
        game.bases = [game.team2_lineup[i]['legal_name'] if i < runners else None for i in range(3)]
        game.pitch_counts[self.name] = pitches
        game._batters_faced[self.name] = 10
        game._half_pitcher_traffic[self.name] = traffic
        total = 0
        for _ in range(6000):
            game._last_mound_visit[self.name] = (last_faced, pitches-3 if last_faced >= 0 else -100)
            total += game._should_visit_mound(self.pitcher)
        return total / 6000

    def test_trouble_and_workload_matter_and_visits_are_spaced(self):
        late_trouble = self.rate(6, 80, 2, traffic=3)
        self.assertGreater(late_trouble, self.rate(2, 15, 1) * 5)
        self.assertGreater(late_trouble, self.rate(6, 25, 2) * 1.1)
        self.assertLess(self.rate(6, 80, 2, traffic=3, last_faced=9), late_trouble / 5)
        self.assertEqual(self.rate(6, 80, 2, traffic=3, last_faced=10), 0)

    def test_visits_do_not_consume_pitch_or_strategy_randomness(self):
        game = self.game
        pitch_state, strategy_state = game.game_rng.getstate(), game.strategy_rng.getstate()
        self.rate(6, 80, 2, traffic=3)
        self.assertEqual(game.game_rng.getstate(), pitch_state)
        self.assertEqual(game.strategy_rng.getstate(), strategy_state)


class TestStrategyDistributions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts = collections.Counter()
        for seed in range(22000, 22200):
            game = new_game(seed)
            game.play_game()
            previous_half, previous_outs, bases = None, 0, {}
            last_visit, previous_pitcher = {}, {}
            for n, play in enumerate(game.gameday_data['liveData']['plays']['allPlays']):
                half = play['about']['inning'], play['about']['isTopInning']
                if half != previous_half:
                    previous_outs, bases = 0, {}
                pitcher = play['matchup']['pitcher']['id']
                pitch, throws, bunt = 0, 0, False
                moves = collections.defaultdict(list)
                for runner in play['runners']:
                    moves[runner['details']['playIndex']].append(runner)
                for event in play['playEvents']:
                    kind = event['details'].get('eventType', '')
                    if event.get('isPitch'):
                        pitch += 1
                        if event.get('isBunt') and not bunt:
                            bunt = True
                            cls.counts['bunts'] += 1
                            cls.counts['bunt_no_outs'] += previous_outs == 0
                            cls.counts['bunt_two_outs_occupied'] += previous_outs == 2 and bool(bases)
                    if event.get('type') == 'pickoff' or kind.startswith('pickoff'):
                        throws += 1
                        base = int(event['details']['code'])
                        cls.counts['pickoffs'] += 1
                        cls.counts['next_base_open'] += base < 3 and base+1 not in bases
                        cls.counts['loaded_pickoffs'] += len(bases) == 3
                    if kind == 'mound_visit':
                        cls.counts['visits'] += 1
                        cls.counts['early_visits'] += half[0] <= 3
                        cls.counts['new_pitcher_visits'] += previous_pitcher.get(half[1]) != pitcher
                        cls.counts['consecutive_pitcher_visits'] += last_visit.get(pitcher) == n-1
                        last_visit[pitcher] = n
                    if kind in ('stolen_base', 'caught_stealing'):
                        cls.counts['steals'] += 1
                        cls.counts['first_pitch_steals'] += pitch == 1
                        if event['details']['runners'][0]['toBase'] == '3B':
                            cls.counts['steals_third'] += 1
                            cls.counts['steals_third_two_outs'] += previous_outs == 2
                    for runner in moves[event['index']]:
                        m, rid = runner['movement'], runner['details']['runner']['id']
                        bases = {b:r for b,r in bases.items() if r != rid}
                        if not m['isOut'] and m.get('end') in ('1B', '2B', '3B'):
                            bases[int(m['end'][0])] = rid
                cls.counts['pickoff_pa'] += throws > 0
                cls.counts['repeat_pickoff_pa'] += throws >= 2
                previous_half, previous_outs = half, play['count']['outs']
                previous_pitcher[half[1]] = pitcher
                bases = {i:play['matchup']['postOn'+name]['id'] for i,name in
                         enumerate(('First', 'Second', 'Third'), 1) if 'postOn'+name in play['matchup']}

    def test_bunts_mostly_start_with_nobody_out(self):
        c = self.counts
        self.assertTrue(0.57 < c['bunt_no_outs'] / c['bunts'] < 0.8, c)
        self.assertEqual(c['bunt_two_outs_occupied'], 0)

    def test_pickoffs_have_a_purpose_and_repeats_are_occasional(self):
        c = self.counts
        self.assertGreater(c['next_base_open'] / c['pickoffs'], 0.93)
        self.assertEqual(c['loaded_pickoffs'], 0)
        self.assertTrue(0.08 < c['repeat_pickoff_pa'] / c['pickoff_pa'] < 0.26, c)

    def test_visits_follow_later_trouble_or_a_new_pitcher(self):
        c = self.counts
        self.assertTrue(0.1 < c['early_visits'] / c['visits'] < 0.26, c)
        self.assertTrue(0.25 < c['new_pitcher_visits'] / c['visits'] < 0.48, c)
        self.assertLess(c['consecutive_pitcher_visits'] / c['visits'], 0.08)

    def test_steals_wait_for_a_pitch_and_third_is_rarely_risked_with_two_outs(self):
        c = self.counts
        self.assertTrue(0.15 < c['first_pitch_steals'] / c['steals'] < 0.35, c)
        self.assertTrue(0.08 < c['steals_third_two_outs'] / c['steals_third'] < 0.3, c)


if __name__ == '__main__':
    unittest.main()
