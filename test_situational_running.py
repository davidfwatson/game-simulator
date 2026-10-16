"""Joint running decisions behind the round-17 blind-judge reports."""
import collections
import random
import unittest
from unittest.mock import patch

import fieldsim
from baseball import BaseballSimulator
from teams import TEAMS


def new_game(seed=1):
    return BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)


class TestComebackerReads(unittest.TestCase):
    def ball(self, release):
        point = fieldsim.polar(53, 10)
        return fieldsim.BattedBall('Groundout', 'P', 'ground_ball', 'P', 10, point, 53,
                                   release=release, release_point=point)

    def test_second_and_third_do_not_both_break_on_a_routine_comebacker(self):
        rng = random.Random(0)
        with patch.object(rng, 'random', return_value=0):
            dests = fieldsim.ground_out_dests(self.ball(1.1), {2: 1.0, 3: 1.0}, 0, 'first', rng)
        self.assertEqual(dests, {3: 4, 2: 2})

    def test_a_slow_comebacker_can_still_move_both_runners(self):
        ball = fieldsim.resolve(50, -20, 1, random.Random(0))
        self.assertEqual((ball.outcome, ball.fielder), ('Groundout', 'P'))
        rng = random.Random(0)
        with patch.object(rng, 'random', return_value=0):
            dests = fieldsim.ground_out_dests(ball, {2: 1.0, 3: 1.0}, 0, 'first', rng)
        self.assertEqual(dests, {3: 4, 2: 3})

    def test_forced_runners_still_advance_when_the_throw_goes_to_first(self):
        dests = fieldsim.ground_out_dests(self.ball(1.1), {1: 1.0, 2: 1.0}, 0, 'first', random.Random(0))
        self.assertEqual(dests, {2: 3, 1: 2})


class TestTwoOutDeepDouble(unittest.TestCase):
    def test_a_runner_can_score_from_first_on_a_deep_gap_double(self):
        counts = collections.Counter()
        point = fieldsim.polar(380, 15)
        for outs in (0, 2):
            for seed in range(600):
                ball = fieldsim.BattedBall('Double', 'RF', 'fly_ball', 'RC', 15, point, 380,
                                           release=6.5, release_point=point)
                dests, thrown = fieldsim.advance_on_hit(ball, 'Double', {1: 1.0}, outs, random.Random(seed))
                counts[outs] += dests.get(1) == 4
                self.assertEqual(set(dests) | set(thrown), {1})
        self.assertGreater(counts[2], 250, counts)
        self.assertGreater(counts[2], counts[0] + 200, counts)
        self.assertLess(counts[2], 550, counts)


class TestRunningStrategy(unittest.TestCase):
    def bunt_rate(self, slot, margin=0):
        game = new_game(543)
        game.inning, game.outs = 8, 1
        game.team2_score, game.team1_score = max(margin, 0), max(-margin, 0)
        return sum(game._bunt_plan(game.team2_lineup[slot])[0] for _ in range(10000)) / 10000

    def test_bunting_for_a_hit_follows_speed_instead_of_a_bottom_order_bonus(self):
        self.assertGreater(self.bunt_rate(1), self.bunt_rate(8) * 3)

    def test_bunts_for_a_hit_are_rare_when_several_runs_are_needed_late(self):
        close = self.bunt_rate(1)
        self.assertLess(self.bunt_rate(1, margin=-4), close / 6)
        self.assertGreater(self.bunt_rate(1, margin=-4), 0)

    def pickoff_rate(self, outs):
        game = new_game(975)
        game.outs = outs
        game.bases = [None, None, game.team2_lineup[1]['legal_name']]
        return sum(game._decide_pickoff_throw(0) == 3 for _ in range(15000)) / 15000

    def test_pickoffs_at_third_favor_one_out_but_two_out_throws_still_exist(self):
        one_out, two_out = self.pickoff_rate(1), self.pickoff_rate(2)
        self.assertGreater(one_out, two_out * 1.8)
        self.assertGreater(two_out, 0.002)

    def test_the_catcher_protects_home_on_a_first_and_third_steal(self):
        game = new_game(146)
        game.outs = 2
        runner = game.team2_lineup[1]
        game._between_pitch_runners, game._pitch_event_seq = [], 0
        for third_occupied in (False, True):
            game.outs = 2
            game.bases = [runner['legal_name'], None,
                          game.team2_lineup[0]['legal_name'] if third_occupied else None]
            with patch.object(game.game_rng, 'random', return_value=0.97):
                caught = game._resolve_steal_attempt(2, [], 0, 1)
            self.assertEqual(caught, not third_occupied)
            self.assertEqual(game.outs, 2 if third_occupied else 3)


class TestRunningDistributions(unittest.TestCase):
    """136 real feeds: first-to-third on two-out singles is 35% on grounders
    and 39% on liners; 77% of empty-base bunt attempts are by faster runners.
    """
    @classmethod
    def setUpClass(cls):
        cls.counts = collections.Counter()
        for seed in range(27000, 27400):
            game = new_game(seed)
            game.play_game()
            players = {p['id']: p for team in (game.team1_data, game.team2_data)
                       for p in team['players'] + team.get('bench', [])}
            half, outs, occupied = None, 0, False
            for play in game.gameday_data['liveData']['plays']['allPlays']:
                current_half = play['about']['inning'], play['about']['isTopInning']
                if current_half != half:
                    outs, occupied = 0, current_half[0] >= 10
                events = play['playEvents']
                if not occupied and any(e.get('isBunt') for e in events):
                    cls.counts['empty_bunts'] += 1
                    batter = players[play['matchup']['batter']['id']]
                    cls.counts['fast_bunts'] += batter['batting_profile']['stealing_tendency'] >= 0.04
                if (outs == 2 and play['result']['eventType'] == 'single'
                        and not any(e['details'].get('runners') for e in events)):
                    hit = next((e['hitData'] for e in events if e.get('hitData')), {})
                    kind = hit.get('trajectory')
                    for runner in play['runners']:
                        movement = runner['movement']
                        if movement.get('originBase') == '1B':
                            cls.counts[kind, 'n'] += 1
                            cls.counts[kind, 'third'] += movement.get('end') == '3B' and not movement['isOut']
                half, outs = current_half, play['count']['outs']
                occupied = any(play['matchup'].get('postOn' + base) for base in ('First', 'Second', 'Third'))

    def test_two_out_ground_ball_singles_allow_first_to_third(self):
        c = self.counts
        rate = c['ground_ball', 'third'] / c['ground_ball', 'n']
        self.assertTrue(0.17 < rate < 0.50, (rate, c))

    def test_two_out_liners_do_not_automatically_send_the_runner_to_third(self):
        c = self.counts
        rate = c['line_drive', 'third'] / c['line_drive', 'n']
        self.assertTrue(0.22 < rate < 0.62, (rate, c))

    def test_most_bases_empty_bunt_attempts_come_from_faster_runners(self):
        c = self.counts
        self.assertTrue(0.20 < c['empty_bunts'] / 400 < 0.65, c)
        self.assertTrue(0.60 < c['fast_bunts'] / c['empty_bunts'] < 0.93, c)


if __name__ == '__main__':
    unittest.main()
