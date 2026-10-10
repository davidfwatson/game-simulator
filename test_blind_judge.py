"""The blind judge's anonymized names must not themselves be a tell."""
import collections
import unittest

import blind_judge
from teams import TEAMS


class TestBlindJudgeNames(unittest.TestCase):
    def test_relievers_are_not_the_same_men_every_game(self):
        """The first reliever of every real and hand-written game was the
        first free roster pitcher, so two of three excerpts could share
        "Colin Miller replaces Joe Gibson"."""
        template = blind_judge.sim_game(1)['gameData']
        game = blind_judge.sleep_game('052')
        firsts = collections.Counter()
        for seed in range(24):
            data = blind_judge.remap_names(game, template, seed=seed)
            again = blind_judge.remap_names(game, template, seed=seed)
            self.assertEqual(data, again)
            order = {}
            for play in data['liveData']['plays']['allPlays']:
                names = order.setdefault(play['about']['isTopInning'], [])
                if play['matchup']['pitcher']['fullName'] not in names:
                    names.append(play['matchup']['pitcher']['fullName'])
            # One name per man: nobody pitches for both sides or under two names.
            self.assertFalse(set(order[True]) & set(order[False]))
            self.assertEqual(len(order[True]), 3)
            self.assertEqual(order[True][0], 'Joe Gibson')
            firsts[order[True][1]] += 1
            pen = {p['legal_name'] for p in TEAMS['BAY_BOMBERS']['players'] if p['position']['code'] == '1'}
            self.assertTrue(set(order[True]) <= pen)
        self.assertGreaterEqual(len(firsts), 4, firsts)
        self.assertLess(max(firsts.values()), 12, firsts)
