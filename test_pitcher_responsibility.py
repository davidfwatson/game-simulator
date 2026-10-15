"""Runs belong to the pitcher who put the scoring runner on base."""
import collections
import unittest
from unittest.mock import patch

from baseball import BaseballSimulator
from teams import TEAMS


class TestPitcherResponsibility(unittest.TestCase):
    def half_inning(self, outcomes, change_after=(1,), top=True, inning=1, game=None):
        if game is None:
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        game.top_of_inning, game.inning = top, inning
        innings = game.gameday_data['liveData']['linescore']['innings']
        while len(innings) < inning:
            innings.append({'num': len(innings) + 1, 'home': {'runs': 0}, 'away': {'runs': 0}})
        outcomes = iter(outcomes)
        plays = game.gameday_data['liveData']['plays']['allPlays']
        start = len(plays)

        def change_pitcher():
            if len(plays) - start in change_after:
                prefix, _, _, bullpen = game._pitching_side()
                game._bring_in(prefix, bullpen, mid_inning=True)

        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            code = {'Walk': 'B', 'Hit By Pitch': 'H', 'Strikeout': 'S'}.get(outcome, 'X')
            event = {'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': 0},
                     'details': {'code': code, 'description': outcome, 'isStrike': code not in ('B', 'H'),
                                 'type': {'code': 'FF', 'description': 'Fastball'}},
                     'pitchData': {'startSpeed': 94.0}}
            return outcome, None, [event]

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                patch.object(game, '_manage_between_innings'), \
                patch.object(game, '_manage_pitching_change', side_effect=change_pitcher):
            game._simulate_half_inning()
        return game, plays[start:]

    def assert_charges(self, game, expected, earned=None):
        earned = expected if earned is None else earned
        recorded, recorded_earned = collections.Counter(), collections.Counter()
        for play in game.gameday_data['liveData']['plays']['allPlays']:
            for runner in play['runners']:
                details = runner['details']
                if details['isScoringEvent']:
                    pid = details['responsiblePitcher']['id']
                    recorded[pid] += 1
                    recorded_earned[pid] += details['earned']
        # Unary + drops zero counts, which Python 3.9 would otherwise compare.
        self.assertEqual(+recorded, +collections.Counter(expected))
        self.assertEqual(+recorded_earned, +collections.Counter(earned))
        prefix, _, _, _ = game._pitching_side()
        box = game.gameday_data['liveData']['boxscore']['teams'][game._pitching_team_key]
        for name, pitcher in getattr(game, f'{prefix}_pitcher_stats').items():
            pid = pitcher['id']
            stats = box['players'][f'ID{pid}']['stats']['pitching']
            self.assertEqual(stats['runs'], expected.get(pid, 0), name)
            self.assertEqual(stats['earnedRuns'], earned.get(pid, 0), name)
            self.assertEqual(game._runs_allowed[name], expected.get(pid, 0), name)
        self.assertEqual(box['teamStats']['pitching']['runs'], sum(expected.values()))
        self.assertEqual(box['teamStats']['pitching']['earnedRuns'], sum(earned.values()))

    def test_inherited_runner_scores_on_a_hit_before_relievers_own_runners(self):
        for top in (True, False):
            with self.subTest(top=top):
                game, plays = self.half_inning(['Triple', 'Single', 'Home Run'] + ['Strikeout'] * 3, top=top)
                starter, reliever = (p['matchup']['pitcher']['id'] for p in plays[:2])
                self.assertNotEqual(starter, reliever)
                self.assert_charges(game, {starter: 1, reliever: 2})
                inherited = next(r for r in plays[1]['runners'] if r['details']['isScoringEvent'])
                self.assertEqual(inherited['details']['runner']['id'], plays[0]['matchup']['batter']['id'])

    def test_forced_inherited_run_and_multiple_pitcher_responsibilities(self):
        for free_pass in ('Walk', 'Hit By Pitch'):
            with self.subTest(free_pass=free_pass):
                game, plays = self.half_inning(['Walk'] * 3 + [free_pass, 'Home Run'] + ['Strikeout'] * 3,
                                               change_after=(3,))
                starter, reliever = (plays[i]['matchup']['pitcher']['id'] for i in (0, 3))
                self.assert_charges(game, {starter: 3, reliever: 2})
                scorer = next(r for r in plays[3]['runners'] if r['details']['isScoringEvent'])
                self.assertEqual(scorer['details']['responsiblePitcher']['id'], starter)

    def test_runner_responsibility_survives_two_pitching_changes(self):
        game, plays = self.half_inning(['Walk', 'Walk', 'Strikeout', 'Strikeout', 'Home Run', 'Strikeout'],
                                      change_after=(1, 4))
        pitchers = [plays[i]['matchup']['pitcher']['id'] for i in (0, 1, 4)]
        self.assertEqual(len(set(pitchers)), 3)
        self.assert_charges(game, dict.fromkeys(pitchers, 1))

    def test_inherited_runner_scores_on_an_out(self):
        for outcome, event in (('Groundout', 'Groundout'), ('Flyout', 'Sac Fly'), ('Double Play', 'Double Play')):
            with self.subTest(outcome=outcome):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                pos = 'CF' if outcome == 'Flyout' else 'SS'
                setup = ['Triple', 'Walk'] if outcome == 'Double Play' else ['Triple']
                strikeouts = 1 if outcome == 'Double Play' else 2
                with patch('baseball.FIELD_SIM', False), \
                        patch.object(game.game_rng, 'choices', return_value=[game.team1_defense[pos]]), \
                        patch.object(game.game_rng, 'random', return_value=0.5):
                    game, plays = self.half_inning(setup + [outcome] + ['Strikeout'] * strikeouts,
                                                   change_after=(len(setup),), game=game)
                starter = plays[0]['matchup']['pitcher']['id']
                self.assertEqual(plays[len(setup)]['result']['event'], event)
                self.assert_charges(game, {starter: 1})

    def test_inherited_run_on_an_error_is_unearned_in_feed_and_box_score(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        with patch.object(game.game_rng, 'choices', return_value=[game.team1_defense['SS']]), \
                patch.object(game.game_rng, 'random', return_value=1.0):
            game, plays = self.half_inning(['Triple', 'Groundout'] + ['Strikeout'] * 3, game=game)
        starter = plays[0]['matchup']['pitcher']['id']
        self.assertEqual(plays[1]['result']['event'], 'Field Error')
        self.assert_charges(game, {starter: 1}, earned={})
        scorer = next(r for r in plays[1]['runners'] if r['details']['isScoringEvent'])
        self.assertTrue(scorer['details']['teamUnearned'])

    def test_runner_reaching_again_in_next_inning_belongs_to_new_pitcher(self):
        game, _ = self.half_inning(['Walk'] + ['Strikeout'] * 3)
        game.team2_batter_idx = 0
        game, plays = self.half_inning(['Home Run'] + ['Strikeout'] * 3,
                                      change_after=(), inning=2, game=game)
        reliever = plays[0]['matchup']['pitcher']['id']
        self.assert_charges(game, {reliever: 1})


if __name__ == '__main__':
    unittest.main()
