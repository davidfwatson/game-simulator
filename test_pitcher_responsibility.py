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
                    self.assertEqual(details['teamUnearned'], not details['earned'])
        self.assertEqual(recorded, collections.Counter(expected))
        self.assertEqual(recorded_earned, collections.Counter(earned))
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

    def test_runner_from_an_earlier_error_is_unearned_after_a_pitching_change(self):
        for top in (True, False):
            with self.subTest(top=top):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                defense = game.team1_defense if top else game.team2_defense
                with patch.object(game.game_rng, 'choices', return_value=[defense['SS']]), \
                        patch.object(game.game_rng, 'random', return_value=1.0):
                    game, plays = self.half_inning(['Groundout', 'Home Run'] + ['Strikeout'] * 3,
                                                   top=top, game=game)
                starter, reliever = (p['matchup']['pitcher']['id'] for p in plays[:2])
                self.assertEqual(plays[0]['result']['event'], 'Field Error')
                self.assert_charges(game, {starter: 1, reliever: 1}, earned={reliever: 1})

    def test_error_runner_scoring_on_an_out_or_a_forced_walk_is_unearned(self):
        for outcome in ('Groundout', 'Flyout', 'Walk'):
            with self.subTest(outcome=outcome):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                original = game._handle_batted_ball_out
                calls = 0

                def field(out_type, batter, context):
                    nonlocal calls
                    calls += 1
                    pos = 'SS' if calls == 1 or outcome == 'Groundout' else 'CF'
                    with patch.object(game.game_rng, 'choices', return_value=[game.team1_defense[pos]]), \
                            patch.object(game.game_rng, 'random', return_value=1.0 if calls == 1 else 0.5):
                        return original(out_type, batter, context)

                script = ['Groundout'] + (['Walk'] * 3 if outcome == 'Walk' else ['Double', outcome])
                script += ['Strikeout'] * (3 if outcome == 'Walk' else 2)
                with patch.object(game, '_handle_batted_ball_out', side_effect=field), \
                        patch.object(game.game_rng, 'random', return_value=0.5):
                    game, plays = self.half_inning(script, change_after=(), game=game)
                self.assertEqual(plays[0]['result']['event'], 'Field Error')
                self.assert_charges(game, {plays[0]['matchup']['pitcher']['id']: 1}, earned={})

    def test_automatic_runner_is_unearned_after_a_pitching_change(self):
        for top in (True, False):
            with self.subTest(top=top):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                with patch.object(game, '_manage_offensive_substitutions', return_value=[]):
                    game, plays = self.half_inning(['Strikeout', 'Home Run'] + ['Strikeout'] * 2,
                                                   top=top, inning=10, game=game)
                starter, reliever = (p['matchup']['pitcher']['id'] for p in plays[:2])
                self.assert_charges(game, {starter: 1, reliever: 1}, earned={reliever: 1})

    def test_pinch_runner_keeps_error_or_automatic_runner_status_and_responsibility(self):
        for automatic in (False, True):
            for top in (True, False):
                with self.subTest(automatic=automatic, top=top):
                    game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                    prefix = 'team2' if top else 'team1'
                    setattr(game, f'{prefix}_batter_idx', 4 if automatic else 3)
                    manage = game._manage_offensive_substitutions
                    plays = game.gameday_data['liveData']['plays']['allPlays']

                    def pinch_run(slot, pitcher):
                        if len(plays) == (0 if automatic else 1):
                            with patch.object(game.strategy_rng, 'random', return_value=0):
                                return manage(slot, pitcher)
                        return []

                    defense = game.team1_defense if top else game.team2_defense
                    with patch.object(game, '_manage_offensive_substitutions', side_effect=pinch_run), \
                            patch.object(game.game_rng, 'choices', return_value=[defense['SS']]), \
                            patch.object(game.game_rng, 'random', return_value=1.0):
                        script = ['Strikeout' if automatic else 'Groundout', 'Home Run']
                        script += ['Strikeout'] * (2 if automatic else 3)
                        game, plays = self.half_inning(script, top=top, inning=10 if automatic else 8, game=game)
                    substitution = next(e for p in plays for e in p['playEvents']
                                        if e.get('position', {}).get('abbreviation') == 'PR')
                    scorer = next(r for r in plays[1]['runners'] if r['movement']['originBase'])
                    self.assertEqual(scorer['details']['runner']['id'], substitution['player']['id'])
                    starter, reliever = (p['matchup']['pitcher']['id'] for p in plays[:2])
                    self.assert_charges(game, {starter: 1, reliever: 1}, earned={reliever: 1})

    def test_error_status_does_not_follow_a_runner_into_the_next_inning(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        with patch.object(game.game_rng, 'choices', return_value=[game.team1_defense['SS']]), \
                patch.object(game.game_rng, 'random', return_value=1.0):
            game, plays = self.half_inning(['Groundout'] + ['Strikeout'] * 3, change_after=(), game=game)
        self.assertEqual(plays[0]['result']['event'], 'Field Error')
        game.team2_batter_idx = 0
        game, plays = self.half_inning(['Home Run'] + ['Strikeout'] * 3,
                                      change_after=(), inning=2, game=game)
        self.assert_charges(game, {plays[0]['matchup']['pitcher']['id']: 1})

    def test_runner_reaching_again_in_next_inning_belongs_to_new_pitcher(self):
        game, _ = self.half_inning(['Walk'] + ['Strikeout'] * 3)
        game.team2_batter_idx = 0
        game, plays = self.half_inning(['Home Run'] + ['Strikeout'] * 3,
                                      change_after=(), inning=2, game=game)
        reliever = plays[0]['matchup']['pitcher']['id']
        self.assert_charges(game, {reliever: 1})


if __name__ == '__main__':
    unittest.main()
