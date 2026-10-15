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

    def half_inning(self, field, seed=1, outs=2, setup=None):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        setup = ['Walk'] * 3 if setup is None else setup
        outcomes = iter(setup + ['Strikeout'] * outs + [field.outcome] + ['Strikeout'] * 3)

        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            code = {'Walk': 'B', 'Strikeout': 'S'}.get(outcome, 'X')
            event = {'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': 0},
                     'details': {'code': code, 'description': outcome, 'isStrike': code != 'B',
                                 'type': {'code': 'FF', 'description': 'Fastball'}},
                     'pitchData': {'startSpeed': 94.0}}
            context = None
            if code == 'X' and len(game.gameday_data['liveData']['plays']['allPlays']) == len(setup) + outs:
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
        return game, game.gameday_data['liveData']['plays']['allPlays'][len(setup) + outs]

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
        # Second is clear for the batter's attempt. The lead runner scores
        # before the tag there; the runner from second has not reached home.
        game, play = self.half_inning(self.ball(release=4.5, batter_out=2), setup=['Walk', 'Double'])
        self.assert_score(game, play, 1)
        by_origin = {r['movement']['originBase']: r for r in play['runners']}
        self.assertEqual(by_origin['3B']['movement']['end'], 'score')
        self.assertEqual(by_origin['2B']['movement']['end'], '3B')
        self.assertFalse(by_origin['2B']['details']['isScoringEvent'])
        self.assertNotIn('throw', by_origin['2B']['details'])
        self.assertEqual(by_origin[None]['movement']['outNumber'], 3)
        self.assertEqual(by_origin[None]['movement']['outBase'], '2B')
        batting = game.gameday_data['liveData']['boxscore']['teams']['away']['players']
        for origin, runs in (('3B', 1), ('2B', 0), (None, 0)):
            pid = by_origin[origin]['details']['runner']['id']
            self.assertEqual(batting[f'ID{pid}']['stats']['batting']['runs'], runs)

        renderer = SayRunners(game.gameday_data, seed=1)
        lines = renderer.render().splitlines()
        low, high = renderer._play_line_map[play['about']['atBatIndex']]
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
        game, play = self.half_inning(self.ball(release=4.0), seed=0)
        self.assert_score(game, play, 1)
        out = next(r for r in play['runners'] if r['movement']['isOut'])
        self.assertEqual(out['movement']['originBase'], '2B')
        self.assertEqual(out['movement']['outBase'], '4B')
        self.assertFalse(out['details']['isScoringEvent'])

    def test_two_out_batter_stretching_preserves_earlier_runs(self):
        for outcome, out_base, release, runs in (('Single', 2, 7.0, 2), ('Double', 3, 11.0, 3)):
            with self.subTest(outcome=outcome):
                game, play = self.half_inning(self.ball(outcome, release, out_base))
                self.assert_score(game, play, runs)
                out = next(r for r in play['runners'] if r['movement']['isOut'])
                self.assertEqual(out['details']['movementReason'], 'r_out_stretching')
                self.assertEqual(out['movement']['outNumber'], 3)

    def test_batter_out_stretching_has_one_movement_and_keeps_his_hit(self):
        for outcome, out_base, release in (('Single', 2, 7.0), ('Double', 3, 11.0)):
            for outs in (0, 2):
                with self.subTest(outcome=outcome, outs=outs):
                    game, play = self.half_inning(self.ball(outcome, release, out_base), outs=outs)
                    batter = play['matchup']['batter']
                    moves = [r for r in play['runners'] if r['details']['runner']['id'] == batter['id']]
                    self.assertEqual(len(moves), 1)
                    movement = moves[0]['movement']
                    self.assertTrue(movement['isOut'])
                    self.assertIsNone(movement['originBase'])
                    self.assertIsNone(movement['end'])
                    self.assertEqual(movement['outBase'], f'{out_base}B')
                    self.assertEqual(movement['outNumber'], outs + 1)
                    self.assertEqual(moves[0]['details']['movementReason'], 'r_out_stretching')
                    self.assertNotIn(batter['fullName'], game.bases)
                    for runner in play['runners']:
                        name, move = runner['details']['runner']['fullName'], runner['movement']
                        if move['isOut'] or move['end'] == 'score':
                            self.assertNotIn(name, game.bases)
                        else:
                            self.assertEqual(game.bases[int(move['end'][0]) - 1], name)
                    box = game.gameday_data['liveData']['boxscore']['teams']
                    batting = box['away']['players'][f"ID{batter['id']}"]['stats']['batting']
                    pitching = box['home']['players'][f"ID{play['matchup']['pitcher']['id']}"]['stats']['pitching']
                    self.assertEqual((batting['hits'], batting['totalBases'], batting['doubles']),
                                     (1, out_base - 1, int(outcome == 'Double')))
                    self.assertEqual((pitching['hits'], pitching['doubles']), (1, int(outcome == 'Double')))
                    self.assertEqual(box['away']['teamStats']['batting']['hits'], 1)
                    self.assertEqual(game.gameday_data['liveData']['linescore']['teams']['away']['hits'], 1)

                    renderer = SayRunners(game.gameday_data, seed=1)
                    lines = renderer.render().splitlines()
                    low, high = renderer._play_line_map[play['about']['atBatIndex']]
                    text = ' '.join(lines[low:high])
                    stretch_hit = 'double' if outcome == 'Single' else 'triple'
                    self.assertRegex(text, rf'thinking {stretch_hit}|stretch it into a {stretch_hit}|trying for a {stretch_hit}')
                    self.assertRegex(text, r'\bout\b')
                    self.assertNotRegex(text, r'\baboard\b|stand-up')

    def test_third_out_at_first_or_on_force_prevents_all_runs(self):
        for pos, spot, event in (('1B', fieldsim.FIRST_BASE, 'Groundout'),
                                 ('SS', fieldsim.SECOND_BASE, 'Forceout')):
            with self.subTest(event=event):
                field = fieldsim.BattedBall('Groundout', pos, 'ground_ball', pos, 0.0, spot, 90,
                                           release=1.0, release_point=spot)
                game, play = self.half_inning(field)
                self.assert_score(game, play, 0)
                self.assertEqual(play['result']['event'], event)

    def test_non_field_hits_cannot_make_a_third_out(self):
        for outcome in ('Single', 'Double'):
            with self.subTest(outcome=outcome), patch('baseball.FIELD_SIM', False):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                game.outs, game.bases = 2, ['First Runner', 'Second Runner', 'Third Runner']
                game._play_field = self.ball(outcome, batter_out=2 if outcome == 'Single' else 3)
                game._thrown_out = []
                batter = game.team2_lineup[0]
                result = game._advance_runners(outcome, batter)
                # Running on contact with two out, the runner from second scores on the single too.
                self.assertEqual(result['runs'], 2)
                self.assertEqual(game.outs, 2)
                self.assertEqual(game._thrown_out, [])
                self.assertIn(batter['legal_name'], game.bases)

    def test_non_field_third_out_at_first_or_on_force_prevents_all_runs(self):
        for force in (False, True):
            with self.subTest(force=force), patch('baseball.FIELD_SIM', False):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                game.outs = 2
                game.bases = ['First Runner', None, 'Third Runner']
                with patch.object(game.game_rng, 'choices', return_value=[game.team1_defense['SS']]), \
                        patch.object(game.game_rng, 'random', side_effect=[0.0, 0.0 if force else 1.0]):
                    result = game._handle_batted_ball_out('Groundout', game.team2_lineup[0])
                self.assertEqual(game.outs, 3)
                self.assertEqual(result[0], 0)
                self.assertEqual(result[2], 0)
                self.assertEqual(result[7], 'Forceout' if force else 'Groundout')

    def test_advancement_continues_when_tag_is_only_the_second_out(self):
        dests, thrown_out = fieldsim.advance_on_hit(self.ball(release=5.5), 'Single',
                                                   {1: 1.0, 2: 1.0, 3: 1.0}, 1, random.Random(22))
        self.assertEqual(dests, {3: 4, 2: 4})
        self.assertEqual(thrown_out, {1: 3})


class TestResponsiblePitcher(unittest.TestCase):
    def test_runner_with_no_recorded_pitcher_is_charged_to_the_pitcher_on_the_mound(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        game.top_of_inning = True
        on_mound = game._pitching_side()[2]
        self.assertIs(game._responsible_pitcher('Nobody Recorded'), on_mound)
        game._runner_pitchers['Someone'] = {'id': 1, 'legal_name': 'Earlier Pitcher'}
        self.assertEqual(game._responsible_pitcher('Someone')['legal_name'], 'Earlier Pitcher')


if __name__ == '__main__':
    unittest.main()
