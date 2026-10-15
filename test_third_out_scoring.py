"""Runs on inning-ending hits depend on when the third out was made."""
import random
import re
import unittest
from unittest.mock import patch

import fieldsim
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS


class SayRunners(NarrativeRenderer):
    def _optional(self, name):
        super()._optional(name)
        return True


class TestThirdOutScoring(unittest.TestCase):
    def ball(self, outcome='Single', release=5.0, batter_out=None):
        return fieldsim.BattedBall(outcome, 'CF', 'line_drive', 'CF', 0.0, (0, 200), 200,
                                  release=release, release_point=(0, 200), batter_out=batter_out)

    def half_inning(self, field, seed=1):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        outcomes = iter(['Walk'] * 3 + ['Strikeout'] * 2 + [field.outcome])

        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            code = {'Walk': 'B', 'Strikeout': 'S'}.get(outcome, 'X')
            event = {'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': 0},
                     'details': {'code': code, 'description': outcome, 'isStrike': code != 'B',
                                 'type': {'code': 'FF', 'description': 'Fastball'}},
                     'pitchData': {'startSpeed': 94.0}}
            context = None
            if code == 'X':
                game._play_field = field
                game.game_rng.seed(seed)
                context = {'batted_ball_data': {'field': field, 'ev': 90.0, 'la': 15.0}}
                event['hitData'] = {'trajectory': field.trajectory, 'location': field.location}
            return outcome, context, [event]

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                patch.object(game, '_manage_between_innings'), \
                patch.object(game, '_manage_pitching_change'), \
                patch.object(game, '_runner_speeds', side_effect=lambda: {
                    i + 1: 1.0 for i, name in enumerate(game.bases) if name}):
            game._simulate_half_inning()
        return game, game.gameday_data['liveData']['plays']['allPlays'][-1]

    def assert_score(self, game, play, runs):
        self.assertEqual(game.outs, 3)
        self.assertEqual(play['count']['outs'], 3)
        self.assertEqual(play['result']['awayScore'], runs)
        self.assertEqual(play['result']['rbi'], runs)
        self.assertEqual(play['about']['isScoringPlay'], bool(runs))
        self.assertEqual(sum(r['details']['isScoringEvent'] for r in play['runners']), runs)
        linescore = game.gameday_data['liveData']['linescore']
        self.assertEqual(linescore['teams']['away']['runs'], runs)
        self.assertEqual(linescore['innings'][0]['away']['runs'], runs)
        pitcher = game.team1_pitcher_stats[game.team1_current_pitcher_name]
        pitching = game.gameday_data['liveData']['boxscore']['teams']['home']['players'][f"ID{pitcher['id']}"]['stats']['pitching']
        self.assertEqual(pitching['outs'], 3)
        self.assertEqual(pitching['runs'], runs)

    def test_two_out_tag_counts_only_runs_before_the_tag(self):
        # The throw to third arrives at 6.459s; second to home takes 6.475s.
        game, play = self.half_inning(self.ball())
        self.assert_score(game, play, 1)
        by_origin = {r['movement']['originBase']: r for r in play['runners']}
        self.assertEqual(by_origin['3B']['movement']['end'], 'score')
        self.assertEqual(by_origin['2B']['movement']['end'], '3B')
        self.assertFalse(by_origin['2B']['details']['isScoringEvent'])
        self.assertNotIn('throw', by_origin['2B']['details'])
        self.assertEqual(by_origin['1B']['movement']['outNumber'], 3)
        self.assertEqual(by_origin['1B']['movement']['outBase'], '3B')
        batting = game.gameday_data['liveData']['boxscore']['teams']['away']['players']
        for origin, runs in (('3B', 1), ('2B', 0), ('1B', 0)):
            pid = by_origin[origin]['details']['runner']['id']
            self.assertEqual(batting[f'ID{pid}']['stats']['batting']['runs'], runs)

        renderer = SayRunners(game.gameday_data, seed=1)
        lines = renderer.render().splitlines()
        low, high = renderer._play_line_map[5]
        text = ' '.join(lines[low:high]).split('...', 1)[-1]
        early = re.escape(by_origin['3B']['details']['runner']['fullName'].split()[-1])
        late = re.escape(by_origin['2B']['details']['runner']['fullName'].split()[-1])
        self.assertRegex(text, rf'{early}[^.]*\b(?:score|scores|scoring)\b')
        self.assertNotRegex(text, rf'{late}[^.]*\b(?:score|scores|scoring)\b')
        self.assertIn(' out at ', play['result']['description'])

    def test_two_out_later_tag_allows_both_earlier_runs(self):
        game, play = self.half_inning(self.ball(release=5.5), seed=5)
        self.assert_score(game, play, 2)

    def test_two_out_runner_tagged_at_home_does_not_score(self):
        game, play = self.half_inning(self.ball(), seed=0)
        self.assert_score(game, play, 1)
        out = next(r for r in play['runners'] if r['movement']['isOut'])
        self.assertEqual(out['movement']['originBase'], '2B')
        self.assertEqual(out['movement']['outBase'], '4B')
        self.assertFalse(out['details']['isScoringEvent'])

    def test_two_out_batter_stretching_preserves_earlier_runs(self):
        for outcome, out_base, release, runs in (('Single', 2, 7.0, 1), ('Double', 3, 10.0, 2)):
            with self.subTest(outcome=outcome):
                game, play = self.half_inning(self.ball(outcome, release, out_base))
                self.assert_score(game, play, runs)
                out = next(r for r in play['runners'] if r['movement']['isOut'])
                self.assertEqual(out['details']['movementReason'], 'r_out_stretching')
                self.assertEqual(out['movement']['outNumber'], 3)

    def test_third_out_at_first_or_on_force_prevents_all_runs(self):
        for pos, spot, event in (('1B', fieldsim.FIRST_BASE, 'Groundout'),
                                 ('SS', fieldsim.SECOND_BASE, 'Forceout')):
            with self.subTest(event=event):
                field = fieldsim.BattedBall('Groundout', pos, 'ground_ball', pos, 0.0, spot, 90,
                                           release=1.0, release_point=spot)
                game, play = self.half_inning(field)
                self.assert_score(game, play, 0)
                self.assertEqual(play['result']['event'], event)

    def test_advancement_continues_when_tag_is_only_the_second_out(self):
        dests, thrown_out = fieldsim.advance_on_hit(self.ball(release=6.5), 'Single',
                                                   {1: 1.0, 2: 1.0, 3: 1.0}, 1, random.Random(1))
        self.assertEqual(dests, {3: 4, 2: 4})
        self.assertEqual(thrown_out, {1: 3})


if __name__ == '__main__':
    unittest.main()
