"""Pitcher decisions use run responsibility, actual outs and entry state."""
import unittest
from unittest.mock import patch

from baseball import BaseballSimulator
from commentary import GAME_CONTEXT
from renderers import NarrativeRenderer
from teams import TEAMS


class SayDecisions(NarrativeRenderer):
    def _optional(self, name):
        super()._optional(name)
        return True


class TestPitcherDecisions(unittest.TestCase):
    def simulate(self, outcomes=None, changes=None):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        outcomes = {(1, False): ['Home Run']} if outcomes is None else outcomes
        changes = dict(changes or {})
        self.pitchers = {}
        for prefix, side in (('team1', 'home'), ('team2', 'away')):
            stats = getattr(game, f'{prefix}_pitcher_stats')
            names = [getattr(game, f'{prefix}_current_pitcher_name')] + getattr(game, f'{prefix}_available_bullpen')
            self.pitchers.update({f'{side}{i}': stats[name] for i, name in enumerate(names)})
        plays = game.gameday_data['liveData']['plays']['allPlays']

        def plate_index():
            return sum(p['about']['inning'] == game.inning and p['about']['isTopInning'] == game.top_of_inning
                       for p in plays)

        def change(mid_inning):
            alias = changes.pop((game.inning, game.top_of_inning, plate_index()), None)
            if alias:
                prefix, _, _, bullpen = game._pitching_side()
                with patch.object(game, '_pick_reliever', return_value=self.pitchers[alias]['legal_name']):
                    game._bring_in(prefix, bullpen, mid_inning)

        def at_bat(batter, pitcher):
            script = outcomes.get((game.inning, game.top_of_inning), [])
            index = plate_index()
            outcome = script[index] if index < len(script) else 'Strikeout'
            code = {'Walk': 'B', 'Strikeout': 'S'}.get(outcome, 'X')
            event = {'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': 0},
                     'details': {'code': code, 'description': outcome, 'isStrike': code != 'B',
                                 'type': {'code': 'FF', 'description': 'Fastball'}},
                     'pitchData': {'startSpeed': 94.0}}
            return outcome, None, [event]

        with patch('baseball.FIELD_SIM', False), \
                patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                patch.object(game, '_manage_between_innings', side_effect=lambda: change(False)), \
                patch.object(game, '_manage_pitching_change', side_effect=lambda: change(True)):
            game.play_game()
        self.assertFalse(changes, 'All scheduled pitching changes should occur')
        return game

    def decision(self, game, role, alias):
        pitcher = self.pitchers[alias]
        self.assertEqual(game.gameday_data['liveData']['decisions'][role],
                         {'id': pitcher['id'], 'fullName': pitcher['legal_name']})

    def pitching(self, game, alias):
        side = 'home' if alias.startswith('home') else 'away'
        pid = self.pitchers[alias]['id']
        return game.gameday_data['liveData']['boxscore']['teams'][side]['players'][f'ID{pid}']['stats']['pitching']

    def test_loss_belongs_to_inherited_go_ahead_runner(self):
        for top, pitching, batting in ((True, 'home', 'away'), (False, 'away', 'home')):
            with self.subTest(top=top):
                game = self.simulate({(1, top): ['Walk', 'Home Run']}, {(1, top, 1): f'{pitching}1'})
                self.decision(game, 'loser', f'{pitching}0')
                self.decision(game, 'winner', f'{batting}0')
                play = next(p for p in game.gameday_data['liveData']['plays']['allPlays']
                            if p['result']['event'] == 'Home Run')
                self.assertEqual(play['matchup']['pitcher']['id'], self.pitchers[f'{pitching}1']['id'])
                self.assertEqual(play['runners'][0]['details']['responsiblePitcher']['id'], self.pitchers[f'{pitching}0']['id'])

    def test_loss_uses_go_ahead_run_not_tying_or_insurance_run(self):
        game = self.simulate({(1, False): ['Home Run'], (2, True): ['Walk', 'Walk', 'Home Run']},
                             {(2, True, 1): 'home1', (2, True, 2): 'home2'})
        # The starter's runner ties it, home1's runner goes ahead, home2's HR adds insurance.
        self.decision(game, 'loser', 'home1')

    def test_later_tie_resets_pitchers_of_record(self):
        game = self.simulate({(1, False): ['Home Run'], (7, True): ['Home Run'], (7, False): ['Home Run']},
                             {(6, True, 0): 'home1', (7, True, 0): 'home2', (7, False, 0): 'away1'})
        self.decision(game, 'winner', 'home2')
        self.decision(game, 'loser', 'away1')

    def test_starter_needs_fifteen_outs(self):
        for inning, winner in ((5, 'home1'), (6, 'home0')):
            with self.subTest(starter_innings=inning - 1):
                game = self.simulate(changes={(inning, True, 0): 'home1'})
                self.assertEqual(self.pitching(game, 'home0')['outs'], (inning - 1) * 3)
                self.decision(game, 'winner', winner)

    def test_short_starter_win_goes_to_more_effective_not_longest_reliever(self):
        game = self.simulate({(1, False): ['Home Run'] * 2, (5, True): ['Home Run']},
                             {(5, True, 0): 'home1', (9, True, 0): 'home2'})
        self.assertEqual(self.pitching(game, 'home1')['outs'], 12)
        self.assertEqual(self.pitching(game, 'home2')['outs'], 3)
        self.decision(game, 'winner', 'home2')
        self.assertNotIn('save', game.gameday_data['liveData']['decisions'])

    def test_effectiveness_uses_run_rate_then_baserunner_rate(self):
        cases = [({(1, False): ['Home Run'] * 4, (5, True): ['Home Run'], (7, True): ['Home Run']},
                  'home2'),
                 ({(1, False): ['Home Run'], (5, True): ['Walk']}, 'home2')]
        for outcomes, winner in cases:
            with self.subTest(outcomes=outcomes):
                game = self.simulate(outcomes, {(5, True, 0): 'home1', (7, True, 0): 'home2'})
                self.decision(game, 'winner', winner)

    def test_equally_effective_relievers_favor_earlier_appearance(self):
        game = self.simulate(changes={(4, True, 0): 'home1', (7, True, 0): 'home2'})
        self.decision(game, 'winner', 'home1')

    def test_effective_reliever_of_record_keeps_win(self):
        game = self.simulate({(6, False): ['Home Run']},
                             {(6, True, 0): 'home1', (7, True, 0): 'home2'})
        self.decision(game, 'winner', 'home1')

    def test_brief_ineffective_reliever_yields_to_effective_successor(self):
        game = self.simulate({(6, True): ['Home Run'] * 2, (6, False): ['Home Run'] * 3},
                             {(6, True, 0): 'home1', (7, True, 0): 'home2'})
        self.assertEqual(self.pitching(game, 'home1')['outs'], 3)
        self.decision(game, 'winner', 'home2')

    def test_brief_ineffective_outing_includes_inherited_earned_runs(self):
        game = self.simulate({(6, True): ['Walk', 'Walk', 'Home Run'], (6, False): ['Home Run'] * 4},
                             {(6, True, 2): 'home1', (7, True, 0): 'home2'})
        self.assertEqual(self.pitching(game, 'home1')['earnedRuns'], 1)
        self.assertEqual(game._mound_earned_runs[self.pitchers['home1']['id']], 3)
        self.decision(game, 'winner', 'home2')

    def test_ineffective_reliever_keeps_win_without_effective_successor(self):
        game = self.simulate({(6, True): ['Home Run'] * 2, (6, False): ['Home Run'] * 8,
                              (7, True): ['Home Run'] * 4},
                             {(6, True, 0): 'home1', (7, True, 0): 'home2'})
        self.decision(game, 'winner', 'home1')

    def test_save_tying_run_on_base_at_bat_or_on_deck(self):
        for lead, runners, save in ((1, 0, True), (2, 0, True), (3, 0, False), (3, 1, True),
                                    (4, 1, False), (4, 2, True), (5, 3, True), (6, 3, False)):
            with self.subTest(lead=lead, runners=runners):
                game = self.simulate({(1, False): ['Home Run'] * lead,
                                      (9, True): ['Walk'] * runners + ['Strikeout'] * 2},
                                     {(9, True, runners + 2): 'home1'})
                self.assertEqual(self.pitching(game, 'home1')['outs'], 1)
                self.assertEqual('save' in game.gameday_data['liveData']['decisions'], save)
                if save:
                    self.decision(game, 'save', 'home1')

    def test_save_three_run_lead_requires_an_inning_unless_tying_run_is_close(self):
        for lead, save in ((3, True), (4, False)):
            with self.subTest(lead=lead):
                game = self.simulate({(1, False): ['Home Run'] * lead}, {(9, True, 0): 'home1'})
                self.assertEqual(self.pitching(game, 'home1')['outs'], 3)
                self.assertEqual('save' in game.gameday_data['liveData']['decisions'], save)

    def test_three_inning_save_has_no_lead_size_limit(self):
        for before, save in ((0, True), (1, False)):
            with self.subTest(outs_before_entry=before):
                game = self.simulate({(1, False): ['Home Run'] * 7}, {(7, True, before): 'home1'})
                self.assertEqual(self.pitching(game, 'home1')['outs'], 9 - before)
                self.assertEqual('save' in game.gameday_data['liveData']['decisions'], save)

    def test_save_requires_an_out(self):
        game = self.simulate(changes={(9, True, 2): 'home1'})
        self.pitching(game, 'home1')['outs'] = 0
        game._record_decisions()
        self.assertNotIn('save', game.gameday_data['liveData']['decisions'])

    def test_finishing_winner_cannot_also_get_a_save(self):
        game = self.simulate(changes={(5, True, 0): 'home1'})
        self.decision(game, 'winner', 'home1')
        self.assertNotIn('save', game.gameday_data['liveData']['decisions'])

    def test_only_finishing_pitcher_gets_save(self):
        game = self.simulate(changes={(6, True, 0): 'home1', (9, True, 0): 'home2'})
        self.decision(game, 'save', 'home2')

    def test_save_uses_entry_lead_before_insurance_runs(self):
        game = self.simulate({(1, False): ['Home Run'], (8, False): ['Home Run'] * 5},
                             {(8, True, 0): 'home1'})
        self.decision(game, 'save', 'home1')

    def test_finisher_entering_tied_or_behind_does_not_get_short_save(self):
        for away_runs in (0, 1):
            with self.subTest(away_runs=away_runs):
                game = self.simulate({(1, True): ['Home Run'] * away_runs,
                                      (8, False): ['Home Run'] * (away_runs + 1)},
                                     {(8, True, 0): 'home1'})
                self.decision(game, 'winner', 'home1')
                self.assertNotIn('save', game.gameday_data['liveData']['decisions'])

    def test_records_mid_inning_entry_score_bases_and_outs(self):
        game = self.simulate({(1, False): ['Home Run'] * 4,
                              (9, True): ['Walk', 'Walk', 'Strikeout', 'Strikeout']},
                             {(9, True, 4): 'home1'})
        entry = game._pitcher_entries[self.pitchers['home1']['id']]
        self.assertEqual((entry['team'], entry['inning'], entry['outs']), ('home', 9, 2))
        self.assertEqual((entry['homeScore'], entry['awayScore']), (4, 0))
        self.assertEqual(sum(bool(name) for name in entry['bases']), 2)
        self.assertEqual(game.bases, entry['bases'])
        self.decision(game, 'save', 'home1')

    def test_between_inning_entry_includes_automatic_runner(self):
        game = self.simulate({(10, True): ['Home Run']}, {(10, False, 0): 'away1'})
        entry = game._pitcher_entries[self.pitchers['away1']['id']]
        self.assertEqual((entry['team'], entry['inning'], entry['outs']), ('away', 10, 0))
        self.assertIsNotNone(entry['bases'][1])
        self.assertEqual((entry['homeScore'], entry['awayScore']), (0, 2))
        self.decision(game, 'save', 'away1')

    def test_boxscore_outs_and_entry_order_survive_old_pa_matchup(self):
        game = self.simulate(changes={(5, True, 2): 'home1'})
        self.assertEqual(self.pitching(game, 'home0')['outs'], 14)
        play = next(p for p in game.gameday_data['liveData']['plays']['allPlays']
                    if p['matchup']['pitcher']['id'] == self.pitchers['home1']['id'])
        # The PA began with the starter; its final out belongs to the reliever.
        play['matchup']['pitcher'] = {'id': self.pitchers['home0']['id'],
                                    'fullName': self.pitchers['home0']['legal_name']}
        game._record_decisions()
        self.decision(game, 'winner', 'home1')

    def test_save_uses_actual_entry_when_matchup_names_previous_pitcher(self):
        game = self.simulate(changes={(9, True, 2): 'home1'})
        play = game.gameday_data['liveData']['plays']['allPlays'][-1]
        play['matchup']['pitcher'] = {'id': self.pitchers['home0']['id'],
                                    'fullName': self.pitchers['home0']['legal_name']}
        game._record_decisions()
        self.decision(game, 'save', 'home1')

    def test_narrative_still_renders_game_lines_decisions_and_postgame(self):
        game = self.simulate(changes={(9, True, 0): 'home1'})
        pools = {'decision_win': ['{pitcher} gets the win.'],
                 'decision_loss': ['{pitcher} takes the loss.'],
                 'decision_save': ['{pitcher} gets the save.']}
        renderer = SayDecisions(game.gameday_data, seed=1)
        with patch.dict(GAME_CONTEXT['narrative_strings'], pools):
            text = renderer.render()
        for alias, phrase in (('home0', 'gets the win'), ('away0', 'takes the loss'), ('home1', 'gets the save')):
            self.assertIn(f"{self.pitchers[alias]['legal_name']} {phrase}", text)
        self.assertIn('Final Score:', text)
        self.assertIn('GAME OVER', text)
        self.assertEqual(renderer._pitcher_lines[self.pitchers['home0']['id']]['strikeouts'], 24)


class TestPitchingOuts(unittest.TestCase):
    def test_caught_stealing_during_pa_is_counted_once_for_each_finish(self):
        for finish in ('Walk', 'Strikeout', 'Groundout'):
            with self.subTest(finish=finish):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                outcomes = iter(['Walk', finish, 'Strikeout', 'Strikeout'])
                calls = 0

                def at_bat(batter, pitcher):
                    nonlocal calls
                    calls += 1
                    events = []
                    if calls == 2:
                        with patch.object(game.game_rng, 'random', return_value=1.0):
                            self.assertTrue(game._resolve_steal_attempt(2, events, 1, 0))
                    return next(outcomes), None, events

                with patch('baseball.FIELD_SIM', False), \
                        patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                        patch.object(game, '_manage_between_innings'), \
                        patch.object(game, '_manage_pitching_change'), \
                        patch.object(game.game_rng, 'random', return_value=0.5):
                    game._simulate_half_inning()
                pitcher = game._pitching_side()[2]
                stats = game.gameday_data['liveData']['boxscore']['teams']['home']
                self.assertEqual(game.outs, 3)
                self.assertEqual(stats['players'][f"ID{pitcher['id']}"]['stats']['pitching']['outs'], 3)
                self.assertEqual(stats['teamStats']['pitching']['outs'], 3)

    def test_strikeout_caught_stealing_double_play_does_not_double_count_outs(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        simulate_at_bat = game._simulate_at_bat
        steals = iter([None, None, 2])
        calls = 0

        def at_bat(batter, pitcher):
            nonlocal calls
            calls += 1
            if calls == 1:
                return 'Walk', None, []
            if calls > 2:
                return 'Strikeout', None, []
            with patch.object(game, '_simulate_pitch_trajectory', return_value=(True, 5)), \
                    patch.object(game, '_simulate_bat_swing', return_value=False), \
                    patch.object(game, '_decide_steal_attempt', side_effect=lambda *args: next(steals)), \
                    patch.object(game.game_rng, 'random', return_value=1.0):
                return simulate_at_bat(batter, pitcher)

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                patch.object(game, '_manage_between_innings'), \
                patch.object(game, '_manage_pitching_change'):
            game._simulate_half_inning()
        stats = game.gameday_data['liveData']['boxscore']['teams']['home']['teamStats']['pitching']
        self.assertEqual(stats['outs'], 3)
        self.assertEqual(game.gameday_data['liveData']['plays']['allPlays'][1]['result']['event'], 'Strikeout Double Play')


if __name__ == '__main__':
    unittest.main()
