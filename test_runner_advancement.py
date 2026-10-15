"""Runner decisions depend on the ball and the other runners on the play."""
import collections
import itertools
import random
import unittest
from unittest.mock import patch

import fieldsim
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS


def ball(pos='SS', release=1.9, outcome='Groundout', trajectory='ground_ball', depth=None, **kwargs):
    distance, spray = fieldsim.POSITIONS[pos]
    distance = distance if depth is None else depth
    point = fieldsim.polar(distance, spray)
    return fieldsim.BattedBall(outcome, pos, trajectory, pos, spray, point, distance,
                              release=release, release_point=point, **kwargs)


class TestGroundBallReads(unittest.TestCase):
    def test_second_holds_on_a_quick_left_side_grounder(self):
        for pos, destination in (('SS', 2), ('3B', 2), ('2B', 3), ('1B', 3)):
            for outs in (0, 1):
                with self.subTest(pos=pos, outs=outs):
                    play, dests = fieldsim.ground_out_play(ball(pos), {2: 1.0}, outs, 1.0, random.Random(0))
                    self.assertEqual(play, 'first')
                    self.assertEqual(dests, {2: destination})

    def test_a_slow_left_side_grounder_gives_second_time_to_go(self):
        for pos in ('SS', '3B'):
            _, dests = fieldsim.ground_out_play(ball(pos, release=2.6), {2: 1.0}, 0, 1.0, random.Random(0))
            self.assertEqual(dests, {2: 3})

    def test_third_holding_blocks_the_runner_from_second(self):
        dests = fieldsim.ground_out_dests(ball('2B'), {2: 1.0, 3: 1.0}, 0, 'first', random.Random(0))
        self.assertEqual(dests, {3: 3, 2: 2})

    def test_force_at_third_preserves_the_other_runners(self):
        dests = fieldsim.ground_out_dests(ball('3B'), {1: 1.0, 2: 1.0}, 0, 'force_third', random.Random(0))
        self.assertEqual(dests, {1: 2})

    def test_non_field_path_uses_the_same_left_side_read(self):
        for pos, expected in (('SS', 1), ('3B', 1), ('2B', 2)):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
            runner = game.team2_lineup[1]['legal_name']
            game.bases = [None, runner, None]
            with patch('baseball.FIELD_SIM', False), \
                    patch.object(game.game_rng, 'choices', return_value=[game.team1_defense[pos]]), \
                    patch.object(game.game_rng, 'random', return_value=0.5):
                game._handle_batted_ball_out('Groundout', game.team2_lineup[0])
            self.assertEqual(game.bases[expected], runner)


class TestBuntAdvancement(unittest.TestCase):
    def test_a_bunt_single_buys_one_base_from_second(self):
        for use_field, outs in itertools.product((False, True), (0, 1, 2)):
            with self.subTest(use_field=use_field, outs=outs):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                runner = game.team2_lineup[1]['legal_name']
                game.outs, game.bases = outs, [None, runner, None]
                with patch('baseball.FIELD_SIM', use_field):
                    result = game._advance_runners('Single', game.team2_lineup[0], is_bunt=True)
                self.assertEqual(result['runs'], 0)
                self.assertEqual(game.bases, [game.team2_lineup[0]['legal_name'], None, runner])

    def test_bunt_runners_wait_for_the_lead_runner(self):
        self.assertEqual(fieldsim.advance_on_bunt({2: 1.0, 3: 1.0}, 0), {3: 3, 2: 2})
        self.assertEqual(fieldsim.advance_on_bunt({1: 1.0, 2: 1.0}, 0), {2: 3, 1: 2})
        self.assertEqual(fieldsim.advance_on_bunt({3: 1.0}, 2), {3: 4})


class TestCaughtBallReads(unittest.TestCase):
    def test_an_infield_liner_never_advances_a_tagging_runner(self):
        for pos in fieldsim.INFIELD:
            dests = fieldsim.tag_ups(ball(pos, trajectory='line_drive'), {1: 1.0, 2: 1.0}, 1, random.Random(0))
            self.assertEqual(dests, {1: 1, 2: 2})

    def test_liners_have_fewer_tags_than_deep_flies(self):
        counts = collections.Counter()
        for trajectory in ('line_drive', 'fly_ball'):
            for seed in range(500):
                dests = fieldsim.tag_ups(ball('RF', trajectory=trajectory, depth=320), {2: 1.0}, 1, random.Random(seed))
                counts[trajectory] += dests[2] == 3
        self.assertGreater(counts['fly_ball'], counts['line_drive'] + 100)

    def test_a_runner_can_be_doubled_off_a_liner(self):
        rng = random.Random(0)
        with patch.object(rng, 'random', return_value=0.0):
            dests, doubled = fieldsim.air_out_play(ball('SS', trajectory='line_drive'), {1: 1.0}, 1, rng)
        self.assertEqual(dests, {})
        self.assertEqual(doubled, {1: 1})
        dests, doubled = fieldsim.air_out_play(ball('SS', trajectory='line_drive'), {1: 1.0}, 3, rng)
        self.assertEqual((dests, doubled), ({1: 1}, {}))


class TestErrorsAndHitTraffic(unittest.TestCase):
    def test_overthrows_and_bobbles_have_different_advancement(self):
        counts = collections.Counter()
        for error_type in ('fielding', 'throwing'):
            for seed in range(500):
                dests, batter_base = fieldsim.advance_on_error(ball('SS'), {1: 1.0, 2: 1.0}, 0,
                                                               random.Random(seed), error_type)
                counts[error_type, 'score'] += dests[2] == 4
                counts[error_type, 'batter_second'] += batter_base == 2
        self.assertLess(counts['fielding', 'score'], 70)
        self.assertEqual(counts['throwing', 'score'], 500)
        self.assertLess(counts['fielding', 'batter_second'], 45)
        self.assertGreater(counts['throwing', 'batter_second'], 130)

    def test_error_destinations_preserve_every_runner_in_order(self):
        for pos, error_type, outs, mask in itertools.product(('P', 'SS', '3B', 'CF', 'RF'),
                                                            ('fielding', 'throwing'), (0, 1, 2), range(1, 8)):
            runners = {base: 1.0 for base in (1, 2, 3) if mask & (1 << (base - 1))}
            field = ball(pos, release=4.0, hang_time=4.0, trajectory='fly_ball' if pos in fieldsim.OUTFIELD else 'ground_ball')
            dests, batter_base = fieldsim.advance_on_error(field, runners, outs, random.Random(mask), error_type)
            with self.subTest(pos=pos, error_type=error_type, outs=outs, mask=mask):
                self.assertEqual(set(dests), set(runners))
                self.assertGreaterEqual(batter_base, 1)
                safe = [d for d in dests.values() if d < 4] + [batter_base]
                self.assertEqual(len(safe), len(set(safe)))
                previous = batter_base
                for base in sorted(dests):
                    self.assertGreaterEqual(dests[base], base)
                    self.assertTrue(dests[base] > previous or dests[base] == 4)
                    previous = dests[base]

    def test_a_deep_drop_does_not_leave_the_batter_at_first(self):
        for seed in range(100):
            dests, batter_base = fieldsim.advance_on_error(
                ball('CF', release=5.0, hang_time=5.0, trajectory='fly_ball', depth=350),
                {2: 1.0}, 0, random.Random(seed))
            self.assertGreaterEqual(batter_base, 2)
            self.assertGreater(dests[2], batter_base)

    def test_batter_holds_when_the_lead_runner_is_stopping_at_third(self):
        field = ball('CF', release=8.0, outcome='Double', trajectory='line_drive', depth=300, batter_out=3)
        dests, thrown_out = fieldsim.advance_on_hit(field, 'Double', {1: 0.9}, 0, random.Random(0))
        self.assertEqual(dests, {1: 3})
        self.assertEqual(thrown_out, {})
        self.assertIsNone(field.batter_out)

    def test_no_third_out_attempt_at_an_occupied_third_base(self):
        for seed in range(100):
            field = ball('CF', release=5.0, outcome='Single', trajectory='line_drive', depth=220)
            dests, thrown_out = fieldsim.advance_on_hit(field, 'Single', {1: 1.1, 2: 0.8}, 2, random.Random(seed))
            self.assertFalse(dests.get(2) == 3 and (dests.get(1) == 3 or thrown_out.get(1) == 3))

    def test_an_error_after_a_hit_keeps_the_hit_and_excludes_the_extra_rbi(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        outcomes = iter(['Double', 'Single'] + ['Strikeout'] * 3)
        field = ball('CF', release=4.0, outcome='Single', trajectory='ground_ball', depth=240)

        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            event = {'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': 0},
                     'details': {'code': 'S' if outcome == 'Strikeout' else 'X', 'description': outcome,
                                 'type': {'code': 'FF', 'description': 'Fastball'}},
                     'pitchData': {'startSpeed': 94.0}}
            if outcome == 'Single':
                game._play_field = field
                event['hitData'] = {'trajectory': 'ground_ball', 'location': 'CF'}
            return outcome, None, [event]

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                patch.object(game, '_manage_between_innings'), \
                patch.object(game, '_manage_pitching_change'), \
                patch.object(game.game_rng, 'random', side_effect=[0.0, 0.9, 0.9]), \
                patch('fieldsim.advance_on_hit', return_value=({2: 3}, {})):
            game._simulate_half_inning()
        play = game.gameday_data['liveData']['plays']['allPlays'][1]
        self.assertEqual(play['result']['eventType'], 'single')
        self.assertEqual(play['result']['rbi'], 0)
        self.assertEqual(play['result']['awayScore'], 1)
        batter = next(r for r in play['runners'] if r['movement']['originBase'] is None)
        scorer = next(r for r in play['runners'] if r['details']['isScoringEvent'])
        self.assertEqual((batter['movement']['start'], batter['movement']['end']), ('1B', '2B'))
        self.assertFalse(scorer['details']['rbi'])
        self.assertFalse(scorer['details']['earned'])
        self.assertEqual(scorer['details']['eventType'], 'error')
        self.assertEqual(game.gameday_data['liveData']['linescore']['teams']['home']['errors'], 1)
        box = game.gameday_data['liveData']['boxscore']['teams']
        self.assertEqual(box['away']['teamStats']['batting']['hits'], 2)
        self.assertEqual(box['home']['teamStats']['fielding']['errors'], 1)
        self.assertEqual(box['home']['teamStats']['pitching']['earnedRuns'], 0)
        renderer = NarrativeRenderer(game.gameday_data, seed=0)
        lines = renderer.render().splitlines()
        start, end = renderer._play_line_map[1]
        text = ' '.join(lines[start:end])
        self.assertIn('error', text)
        self.assertIn('second', text)


class TestRunnerFeedConsistency(unittest.TestCase):
    def test_runner_movements_match_the_score_and_occupied_bases(self):
        doubled = errors_at_second = bunt_singles = 0
        for seed in range(28000, 28200):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
            game.play_game()
            previous = None
            for play in game.gameday_data['liveData']['plays']['allPlays']:
                same_half = previous and previous['about']['inning'] == play['about']['inning'] \
                    and previous['about']['isTopInning'] == play['about']['isTopInning']
                before_outs = previous['count']['outs'] if same_half else 0
                if any('hitData' in e for e in play['playEvents']):
                    self.assertEqual(play['count']['outs'], before_outs + sum(r['movement']['isOut'] for r in play['runners']))
                post = {b: play['matchup'][key]['id'] for key, b in (('postOnFirst', '1B'), ('postOnSecond', '2B'), ('postOnThird', '3B'))
                        if key in play['matchup']}
                terminal = max((e['index'] for e in play['playEvents']), default=0)
                safe = {}
                for runner in play['runners']:
                    if runner['details']['playIndex'] != terminal:
                        continue
                    move = runner['movement']
                    if not move['isOut'] and move['end'] in ('1B', '2B', '3B'):
                        self.assertNotIn(move['end'], safe)
                        safe[move['end']] = runner['details']['runner']['id']
                    doubled += runner['details']['movementReason'] == 'r_doubled_off'
                    errors_at_second += play['result']['event'] == 'Field Error' and move['originBase'] is None and move['end'] == '2B'
                    if play['result']['event'] == 'Field Error' and move['originBase'] is None and move['end'] in ('2B', '3B'):
                        self.assertEqual(move['start'], '1B')
                for base, rid in safe.items():
                    self.assertEqual(post.get(base), rid)
                if play['result']['event'] == 'Single' and any(e.get('isBunt') and e['details'].get('code') == 'X' for e in play['playEvents']):
                    bunt_singles += 1
                    self.assertFalse(any(r['movement']['originBase'] == '2B' and r['details']['isScoringEvent'] for r in play['runners']
                                         if r['details']['playIndex'] == terminal))
                previous = play
            runs = sum(r['details']['isScoringEvent'] for p in game.gameday_data['liveData']['plays']['allPlays'] for r in p['runners'])
            self.assertEqual(runs, game.team1_score + game.team2_score)
        self.assertGreater(doubled, 2)
        self.assertGreater(errors_at_second, 3)
        self.assertGreater(bunt_singles, 20)


if __name__ == '__main__':
    unittest.main()
