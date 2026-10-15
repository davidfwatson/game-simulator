"""Pitch choices follow a pitcher's repertoire, the count and batter's side."""

import collections
import copy
import random
import statistics
import unittest

from baseball import BaseballSimulator
from commentary import GAME_CONTEXT
from renderers import NarrativeRenderer, StatcastRenderer
from teams import TEAMS

FASTBALLS = ('FF', 'SI', 'FC')
OFF_SPEED = ('CH', 'FS')
SLIDERS = ('SL', 'ST')


def share(pitches, types):
    return sum(pitches[t] for t in types) / sum(pitches.values())


class TestPitchMix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts = collections.defaultdict(collections.Counter)
        cls.hands = collections.defaultdict(collections.Counter)
        cls.starters, cls.relievers, cls.short_relievers = [], [], []
        for seed in range(15000, 15100):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
            game.play_game()
            outings = collections.defaultdict(collections.Counter)
            starters = {}
            for play in game.gameday_data['liveData']['plays']['allPlays']:
                matchup = play['matchup']
                pid = matchup['pitcher']['id']
                starters.setdefault(play['about']['isTopInning'], pid)
                hand = 'same' if matchup['pitchHand']['code'] == matchup['batSide']['code'] else 'opposite'
                for event in play['playEvents']:
                    if not event.get('isPitch'):
                        continue
                    kind = event['details']['type']['code']
                    count = event['count']
                    cls.counts[count['balls'], count['strikes']][kind] += 1
                    cls.hands[hand][kind] += 1
                    outings[pid][kind] += 1
            for pid, pitches in outings.items():
                if pid in starters.values():
                    cls.starters.append(pitches)
                else:
                    cls.relievers.append(pitches)
                    if sum(pitches.values()) <= 20:
                        cls.short_relievers.append(pitches)

    def test_fastballs_follow_the_count(self):
        # Real feeds: 95% on 3-0, 72-77% on 2-0/3-1, 43-44% on 0-2/1-2.
        self.assertTrue(0.88 < share(self.counts[3, 0], FASTBALLS) < 0.99)
        for count in ((2, 0), (3, 1)):
            self.assertTrue(0.65 < share(self.counts[count], FASTBALLS) < 0.86, count)
        for count in ((0, 2), (1, 2)):
            self.assertTrue(0.35 < share(self.counts[count], FASTBALLS) < 0.52, count)
        self.assertGreater(share(self.counts[3, 1], FASTBALLS) - share(self.counts[1, 2], FASTBALLS), 0.22)

    def test_secondaries_follow_the_batters_side(self):
        same, opposite = self.hands['same'], self.hands['opposite']
        self.assertGreater(share(opposite, OFF_SPEED), 1.8 * share(same, OFF_SPEED))
        self.assertGreater(share(same, SLIDERS), 1.35 * share(opposite, SLIDERS))

    def test_outings_have_main_pitches_and_a_few_extras(self):
        # Real top three shares: starters 40/26/17%, relievers 52/29/13%.
        for outings, bounds in ((self.starters, ((0.35, 0.50), (0.19, 0.31), (0.12, 0.23))),
                                (self.relievers, ((0.46, 0.62), (0.23, 0.37), (0.07, 0.19)))):
            shares = [sorted(p.values(), reverse=True) + [0, 0, 0] for p in outings]
            totals = [sum(p.values()) for p in outings]
            for index, (low, high) in enumerate(bounds):
                usage = statistics.mean(s[index] / total for s, total in zip(shares, totals))
                self.assertTrue(low < usage < high, (index, usage))
        self.assertTrue(4.2 < statistics.mean(map(len, self.starters)) <= 5.0)
        self.assertTrue(2.6 < statistics.mean(map(len, self.relievers)) < 3.7)
        self.assertTrue(2.4 < statistics.mean(map(len, self.short_relievers)) < 3.6)


class TestPitchArsenalSelection(unittest.TestCase):
    def setUp(self):
        self.game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=19)

    def test_every_roster_has_valid_weighted_repertoires(self):
        for team in TEAMS.values():
            for pitcher in team['players']:
                if 'pitch_arsenal' not in pitcher:
                    continue
                arsenal = pitcher['pitch_arsenal']
                with self.subTest(pitcher=pitcher['legal_name']):
                    self.assertAlmostEqual(sum(p['prob'] for p in arsenal.values()), 1.0)
                    self.assertTrue(all(p['prob'] > 0 for p in arsenal.values()))
                    primary_fastball = max(p['prob'] for name, p in arsenal.items()
                                           if GAME_CONTEXT['PITCH_TYPE_MAP'][name] in FASTBALLS)
                    self.assertTrue(0.35 <= primary_fastball <= 0.55)
                    self.assertLessEqual(len(arsenal), 5 if pitcher['type'] == 'Starter' else 4)
                    self.assertGreaterEqual(sum(sorted((p['prob'] for p in arsenal.values()), reverse=True)[:3]), 0.8)

    def test_switch_hitters_use_the_opposite_side_of_both_pitcher_hands(self):
        pitcher = copy.deepcopy(next(p for p in TEAMS['BAY_BOMBERS']['players'] if p.get('type') == 'Starter'))
        for pitcher_hand, batter_hand in (('R', 'L'), ('L', 'R')):
            pitcher['pitchHand']['code'] = pitcher_hand
            self.game.game_rng.seed(412)
            switched = [self.game._select_pitch_type(pitcher, {'batSide': {'code': 'S'}}, 1, 2)
                        for _ in range(200)]
            self.game.game_rng.seed(412)
            explicit = [self.game._select_pitch_type(pitcher, {'batSide': {'code': batter_hand}}, 1, 2)
                        for _ in range(200)]
            self.assertEqual(switched, explicit)

    def test_the_pitchers_own_weights_survive_missing_handedness(self):
        pitcher = {'pitch_arsenal': {'slider': {'prob': 0.90}, 'sweeper': {'prob': 0.10}}}
        pitches = collections.Counter(self.game._select_pitch_type(pitcher, {}, 3, 0) for _ in range(5000))
        self.assertTrue(0.87 < pitches['slider'] / 5000 < 0.93)
        self.assertEqual(set(pitches), set(pitcher['pitch_arsenal']))

    def test_handedness_changes_choices_for_lefties_and_righties(self):
        for pitcher_hand in ('R', 'L'):
            pitcher = {'pitchHand': {'code': pitcher_hand}, 'pitch_arsenal': {
                'sinker': {'prob': 0.45}, 'sweeper': {'prob': 0.30}, 'changeup': {'prob': 0.25}}}
            choices = {}
            for hand in ('R', 'L'):
                self.game.game_rng = random.Random(817)
                choices[hand] = collections.Counter(self.game._select_pitch_type(
                    pitcher, {'batSide': {'code': hand}}, 1, 1) for _ in range(5000))
            same = choices[pitcher_hand]
            opposite = choices['L' if pitcher_hand == 'R' else 'R']
            self.assertGreater(opposite['changeup'], 2 * same['changeup'])
            self.assertGreater(same['sweeper'], 1.4 * opposite['sweeper'])

    def test_every_pitch_code_and_name_reaches_both_renderers(self):
        details = {name: values for team in TEAMS.values() for pitcher in team['players']
                   for name, values in pitcher.get('pitch_arsenal', {}).items()}
        for name, code in GAME_CONTEXT['PITCH_TYPE_MAP'].items():
            with self.subTest(pitch=name):
                home, away = copy.deepcopy(TEAMS['BAY_BOMBERS']), copy.deepcopy(TEAMS['PC_PILOTS'])
                for pitcher in home['players'] + away['players']:
                    if 'pitch_arsenal' in pitcher:
                        pitcher['pitch_arsenal'] = {name: dict(details[name], prob=1.0)}
                game = BaseballSimulator(home, away, game_seed=91)
                game.play_game()
                for play in game.gameday_data['liveData']['plays']['allPlays']:
                    for event in play['playEvents']:
                        if event.get('isPitch'):
                            self.assertEqual(event['details']['type'], {'code': code, 'description': name.capitalize()})
                spoken = 'fastball' if name == 'four-seam fastball' else name
                self.assertIn(spoken, NarrativeRenderer(game.gameday_data, seed=91).render().lower())
                self.assertIn(name, StatcastRenderer(game.gameday_data, seed=91).render().lower())


if __name__ == '__main__':
    unittest.main()
