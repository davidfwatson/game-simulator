"""Lineup changes and incidental actions, calibrated against 136 MLB feeds."""
import collections
import copy
import unittest
from unittest.mock import patch

from anonymize_real_gameday import anonymize_gameday_data
from baseball import BaseballSimulator
from blind_judge import player_sides
from renderers import NarrativeRenderer
from teams import TEAMS


def simulate(seed):
    game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
    game.play_game()
    return game


class TestSubstitutionState(unittest.TestCase):
    def setUp(self):
        self.game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=1)

    def test_benches_have_distinct_ids_and_do_not_expand_the_starting_lineup(self):
        ids = [p['id'] for team in TEAMS.values() for p in team['bench']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(self.game.team1_lineup), 9)
        self.assertEqual(len(self.game.team2_lineup), 9)
        self.assertEqual(len(self.game.team1_bench), 4)
        self.assertEqual(len(self.game.team2_bench), 4)

    def test_pinch_hitter_inherits_the_slot_and_then_takes_the_field(self):
        game = self.game
        outgoing, incoming = game.team2_lineup[7], game.team2_bench[1]
        event = game._substitute('team2', 7, incoming, 'PH')
        self.assertEqual(event['position']['abbreviation'], 'PH')
        self.assertEqual(event['replacedPlayer']['id'], outgoing['id'])
        self.assertEqual(event['battingOrder'], '801')
        self.assertTrue(event['isSubstitution'])
        self.assertIs(game.team2_lineup[7], incoming)
        self.assertNotIn(incoming, game.team2_bench)
        self.assertNotIn(outgoing, game.team2_lineup)
        box = game.gameday_data['liveData']['boxscore']['teams']['away']
        self.assertEqual(box['battingOrder'][7], incoming['id'])
        self.assertEqual(box['players'][f"ID{outgoing['id']}"]['battingOrder'], '800')
        self.assertEqual(box['players'][f"ID{incoming['id']}"]['stats']['batting']['gamesPlayed'], 1)
        game.top_of_inning = False
        switches = game._manage_defensive_substitutions()
        self.assertEqual(switches[0]['details']['eventType'], 'defensive_switch')
        self.assertIs(game.team2_defense['SS'], incoming)
        self.assertEqual(incoming['position']['abbreviation'], 'SS')

    def test_pinch_runner_replaces_the_runner_and_bats_in_his_slot(self):
        game = self.game
        game.inning, game.team2_score = 8, 1
        outgoing = game.team2_lineup[3]
        game.bases[0] = outgoing['legal_name']
        pitcher = game.team1_pitcher_stats[game.team1_current_pitcher_name]
        with patch.object(game.game_rng, 'random', return_value=0):
            events = game._manage_offensive_substitutions(2, pitcher)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event['position']['abbreviation'], 'PR')
        self.assertEqual(event['replacedPlayer']['id'], outgoing['id'])
        incoming = game.team2_lineup[3]
        self.assertEqual(game.bases[0], incoming['legal_name'])
        self.assertEqual(event['player']['id'], incoming['id'])
        self.assertEqual(event['battingOrder'], '401')
        self.assertIsNot(game.team2_lineup[2], incoming)

    def test_defensive_replacement_can_move_the_center_fielder_to_a_corner(self):
        game = self.game
        game.inning, game.team1_score = 8, 2
        game.team1_bench[:] = [game.team1_bench[2]]
        center = game.team1_lineup[0]
        with patch.object(game.game_rng, 'random', return_value=0):
            events = game._manage_defensive_substitutions()
        self.assertEqual([e['details']['eventType'] for e in events],
                         ['defensive_switch', 'defensive_substitution'])
        self.assertIs(game.team1_defense['LF'], center)
        self.assertEqual(game.team1_defense['CF']['legal_name'], 'Cody Bennett')
        self.assertEqual(len({p['id'] for p in game.team1_defense.values()}), 9)

    def test_games_do_not_mutate_shared_rosters(self):
        before = copy.deepcopy(TEAMS)
        simulate(3)
        self.assertEqual(TEAMS, before)

    def test_anonymizer_keeps_substitutions_and_mound_visits(self):
        data = simulate(17000).gameday_data
        expected = [e for p in data['liveData']['plays']['allPlays'] for e in p['playEvents']
                    if e['details'].get('eventType') in ('offensive_substitution', 'defensive_substitution',
                                                        'defensive_switch', 'mound_visit')]
        self.assertTrue(any(e.get('isSubstitution') for e in expected))
        self.assertTrue(any(e['details']['eventType'] == 'mound_visit' for e in expected))
        # A live feed carries pitchData only on pitches; substitution metadata
        # has to survive its separate non-pitch path.
        result = anonymize_gameday_data(data, TEAMS, seed=10)
        actual = [e for p in result['liveData']['plays']['allPlays'] for e in p['playEvents']
                  if e['details'].get('eventType') in ('offensive_substitution', 'defensive_substitution',
                                                      'defensive_switch', 'mound_visit')]
        self.assertEqual(len(actual), len(expected))
        players = result['gameData']['players']
        for before, after in zip(expected, actual):
            self.assertEqual(before['details']['eventType'], after['details']['eventType'])
            self.assertFalse(after['isPitch'])
            if before.get('isSubstitution'):
                self.assertTrue(after['isSubstitution'])
                self.assertEqual(before['position'], after['position'])
                self.assertEqual(before['battingOrder'], after['battingOrder'])
                self.assertIn(f"ID{after['player']['id']}", players)

    def test_judge_keeps_a_substitute_on_his_team_even_if_he_never_bats(self):
        data = simulate(17000).gameday_data
        play = data['liveData']['plays']['allPlays'][0]
        play['playEvents'].insert(0, {
            'player': {'id': 987654}, 'replacedPlayer': play['matchup']['batter'],
            'details': {'eventType': 'offensive_substitution'},
        })
        self.assertEqual(player_sides(data)[987654], 'away')

    def test_substitution_slot_overrides_a_bench_placeholder_order(self):
        game = self.game
        box = game.gameday_data['liveData']['boxscore']['teams']['away']
        incoming, outgoing = game.team2_bench[0], game.team2_lineup[8]
        box['players'][f"ID{incoming['id']}"]['battingOrder'] = '100'
        event = {'player': {'id': incoming['id']}, 'replacedPlayer': {'id': outgoing['id']},
                 'details': {'eventType': 'offensive_substitution'}}
        game.gameday_data['liveData']['plays']['allPlays'] = [
            {'about': {'isTopInning': True}, 'playEvents': [event]}]
        renderer = NarrativeRenderer(game.gameday_data)
        self.assertEqual(renderer._batting_slot('away', incoming['id']), 8)

    def test_a_pickoff_for_the_third_out_does_not_skip_the_batter(self):
        game = self.game
        outcomes = iter(('Walk', 'Strikeout', 'Strikeout', 'Pickoff 1B'))
        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            if outcome.startswith('Pickoff'):
                with patch.object(game.game_rng, 'random', side_effect=[0.01, 0.9]):
                    events = []
                    game._record_pickoff_throw(events, 1, 1, pitcher)
                return outcome, None, events
            return outcome, None, []
        with patch.object(game, '_simulate_at_bat', side_effect=at_bat):
            game._simulate_half_inning()
        self.assertEqual(game.outs, 3)
        self.assertEqual(game.team2_batter_idx, 3)
        play = game.gameday_data['liveData']['plays']['allPlays'][-1]
        self.assertEqual(play['result']['eventType'], 'pickoff_1b')
        self.assertEqual(len(play['runners']), 1)
        self.assertEqual([c['credit'] for c in play['runners'][0]['credits']], ['assist', 'putout'])
        self.assertEqual(play['runners'][0]['movement']['outNumber'], 3)
        renderer = NarrativeRenderer(game.gameday_data)
        text = renderer.render()
        self.assertIn('picked off', text)
        self.assertNotIn('gets back safely', text)
        self.assertNotIn(play['matchup']['batter']['id'], renderer.batter_history)

    def test_a_pickoff_error_advances_runners_without_an_out(self):
        game = self.game
        game.bases[:2] = [p['legal_name'] for p in game.team2_lineup[:2]]
        game._between_pitch_runners = []
        pitcher = game.team1_pitcher_stats[game.team1_current_pitcher_name]
        events = []
        with patch.object(game.game_rng, 'random', return_value=0.035):
            game._record_pickoff_throw(events, 0, 1, pitcher)
        self.assertEqual(game.outs, 0)
        self.assertIsNone(game.bases[0])
        self.assertEqual(game.bases[1:], [p['legal_name'] for p in game.team2_lineup[:2]])
        self.assertEqual(events[0]['details']['eventType'], 'pickoff_error_1b')
        self.assertEqual(len(game._between_pitch_runners), 2)
        self.assertEqual(game.gameday_data['liveData']['linescore']['teams']['home']['errors'], 1)


class TestGameTexture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = [simulate(seed).gameday_data for seed in range(17000, 17200)]
        cls.counts = collections.Counter()
        for data in cls.games:
            slots = {p['person']['id']: int(p['battingOrder']) // 100
                     for box in data['liveData']['boxscore']['teams'].values()
                     for p in box['players'].values() if p.get('battingOrder')}
            for play in data['liveData']['plays']['allPlays']:
                bunt = False
                for event in play['playEvents']:
                    details = event['details']
                    kind = details.get('eventType', '')
                    if event.get('isSubstitution'):
                        cls.counts[event['position']['abbreviation'] if kind == 'offensive_substitution' else kind] += 1
                    if event.get('type') == 'pickoff' or kind.startswith('pickoff'):
                        cls.counts['pickoff_throws'] += 1
                        cls.counts['pickoff_outs'] += details.get('isOut', False)
                        cls.counts[f"pickoff_base_{details['code']}"] += 1
                    cls.counts['mound_visit'] += kind == 'mound_visit'
                    if event.get('isPitch') and event.get('isBunt'):
                        bunt = True
                        cls.counts['foul_bunts'] += 'Foul Bunt' == details.get('description')
                        if details.get('code') == 'X':
                            cls.counts['bunt_hits'] += play['result']['eventType'] == 'single'
                if bunt:
                    cls.counts['bunt_pa'] += 1
                    slot = slots[play['matchup']['batter']['id']]
                    cls.counts['bunt_bottom'] += slot >= 7
                    cls.counts[f'bunt_slot_{slot}'] += 1
                cls.counts['sac_bunts'] += play['result']['eventType'] == 'sac_bunt'

    def rate(self, key):
        return self.counts[key] / len(self.games)

    def test_position_player_changes_are_normal_game_events(self):
        # Real per game: PH 1.87, PR 0.37, defensive sub 1.01, switch 2.47.
        for key, low, high in [('PH', 1.2, 2.6), ('PR', 0.15, 0.65),
                               ('defensive_substitution', 0.5, 1.6), ('defensive_switch', 1.4, 3.4)]:
            with self.subTest(kind=key):
                self.assertTrue(low < self.rate(key) < high, self.rate(key))

    def test_pickoff_throws_sometimes_get_an_out(self):
        self.assertTrue(2.7 < self.rate('pickoff_throws') < 5.2, self.rate('pickoff_throws'))
        self.assertTrue(0.02 < self.rate('pickoff_outs') < 0.22, self.rate('pickoff_outs'))
        self.assertTrue(0.08 < self.rate('pickoff_base_2') < 0.65, self.rate('pickoff_base_2'))
        self.assertTrue(0.01 < self.rate('pickoff_base_3') < 0.25, self.rate('pickoff_base_3'))

    def test_bunts_include_base_hits_and_mostly_come_from_the_bottom(self):
        # Real: 1.29 attempted PAs, 0.57 foul bunts, 0.31 sacrifices, 0.21 bunt hits.
        for key, low, high in [('bunt_pa', 0.8, 1.85), ('foul_bunts', 0.25, 1.0),
                               ('sac_bunts', 0.12, 0.55), ('bunt_hits', 0.06, 0.42)]:
            with self.subTest(kind=key):
                self.assertTrue(low < self.rate(key) < high, self.rate(key))
        self.assertGreater(self.counts['bunt_bottom'] / self.counts['bunt_pa'], 0.55)
        self.assertGreater(self.rate('bunt_slot_9'), 0.15)
        self.assertLess((self.counts['bunt_slot_3'] + self.counts['bunt_slot_4']) / self.counts['bunt_pa'], 0.1)

    def test_catchers_have_occasional_mound_conferences(self):
        self.assertTrue(4.5 < self.rate('mound_visit') < 8.5, self.rate('mound_visit'))

    def test_batting_order_continues_after_every_kind_of_substitution(self):
        for data in self.games:
            boxes = data['liveData']['boxscore']['teams']
            orders = {side: [p['person']['id'] for p in sorted(
                (p for p in box['players'].values() if p.get('battingOrder') and int(p['battingOrder']) % 100 == 0),
                key=lambda p: int(p['battingOrder']))] for side, box in boxes.items()}
            cursors = {'home': 0, 'away': 0}
            for play in data['liveData']['plays']['allPlays']:
                batting = 'away' if play['about']['isTopInning'] else 'home'
                for event in play['playEvents']:
                    if not event.get('isSubstitution') or event['details']['eventType'] == 'defensive_switch':
                        continue
                    side = batting if event['details']['eventType'] == 'offensive_substitution' else ('home' if batting == 'away' else 'away')
                    slot = int(event['battingOrder']) // 100 - 1
                    self.assertEqual(orders[side][slot], event['replacedPlayer']['id'])
                    self.assertNotIn(event['player']['id'], orders[side])
                    orders[side][slot] = event['player']['id']
                self.assertEqual(play['matchup']['batter']['id'], orders[batting][cursors[batting]])
                if not play['result']['event'].startswith(('Pickoff', 'Caught Stealing')):
                    cursors[batting] = (cursors[batting] + 1) % 9

    def test_every_out_is_charged_to_a_pitcher_once(self):
        for data in self.games:
            outs = {'home': collections.Counter(), 'away': collections.Counter()}
            previous_half, previous_outs = None, 0
            for play in data['liveData']['plays']['allPlays']:
                half = play['about']['inning'], play['about']['isTopInning']
                if half != previous_half:
                    previous_outs = 0
                side = 'home' if half[1] else 'away'
                outs[side][play['matchup']['pitcher']['id']] += play['count']['outs'] - previous_outs
                previous_half, previous_outs = half, play['count']['outs']
            for side, by_pitcher in outs.items():
                box = data['liveData']['boxscore']['teams'][side]
                self.assertEqual(box['teamStats']['pitching']['outs'], sum(by_pitcher.values()))
                for pid, count in by_pitcher.items():
                    self.assertEqual(box['players'][f'ID{pid}']['stats']['pitching']['outs'], count)

    def test_completed_pa_and_runner_indices_survive_prepended_actions(self):
        for data in self.games:
            completed = collections.Counter()
            for play in data['liveData']['plays']['allPlays']:
                side = 'away' if play['about']['isTopInning'] else 'home'
                if play['about'].get('isComplete') is not False:
                    completed[side] += 1
                events = play['playEvents']
                self.assertEqual([e['index'] for e in events], list(range(len(events))))
                for runner in play['runners']:
                    index = runner['details']['playIndex']
                    if runner['details']['movementReason'] in ('r_pickoff', 'r_caught_stealing'):
                        self.assertTrue(0 <= index < len(events))
                        self.assertFalse(events[index]['isPitch'])
                        self.assertTrue(events[index]['details'].get('runners'))
            for side, box in data['liveData']['boxscore']['teams'].items():
                self.assertEqual(box['teamStats']['batting']['plateAppearances'], completed[side])
                self.assertEqual(sum(p['stats']['batting'].get('plateAppearances', 0)
                                     for p in box['players'].values()), completed[side])

    def test_renderer_announces_changes_without_putting_substitutes_in_starting_lineups(self):
        data = self.games[0]
        renderer = NarrativeRenderer(data)
        text = renderer.render()
        lines = text.splitlines()
        pregame = '\n'.join(lines[:renderer._play_line_map[0][0]])
        for box in data['liveData']['boxscore']['teams'].values():
            for player in box['players'].values():
                if player.get('battingOrder') and int(player['battingOrder']) % 100:
                    self.assertNotIn(player['person']['fullName'], pregame)
        self.assertRegex(text, r'pinch[- ]hit')
        self.assertNotIn('Offensive Substitution:', text)
        self.assertNotIn('Defensive Substitution:', text)
        pr_game = next(d for d in self.games if any(e.get('position', {}).get('abbreviation') == 'PR'
                       for p in d['liveData']['plays']['allPlays'] for e in p['playEvents']))
        self.assertIn('comes in to run for', NarrativeRenderer(pr_game).render())


if __name__ == '__main__':
    unittest.main()
