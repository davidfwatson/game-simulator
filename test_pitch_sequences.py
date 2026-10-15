"""Pitch-sequence tells, compared with 136 complete real 2026 feeds."""
import collections
import statistics
import unittest

from baseball import BaseballSimulator
from teams import TEAMS


class TestPitchSequences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lengths, cls.fouls, cls.longest, cls.runs = [], [], [], []
        cls.reached = collections.Counter()
        cls.pitches = collections.Counter()
        cls.swings = collections.Counter()
        cls.foul_pitches = collections.Counter()
        cls.in_play = collections.Counter()
        cls.after_fouls = collections.Counter()
        cls.fouls_after_fouls = collections.Counter()
        cls.outcomes = collections.Counter()
        for seed in range(9000, 9200):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
            game.play_game()
            data = game.gameday_data
            scores = data['liveData']['linescore']['teams']
            cls.runs.extend(scores[side]['runs'] for side in ('home', 'away'))
            for play in data['liveData']['plays']['allPlays']:
                if play['result']['event'] == 'Caught Stealing':
                    continue
                cls.outcomes[play['result']['eventType']] += 1
                events = [e for e in play['playEvents'] if e.get('isPitch')]
                cls.lengths.append(len(events))
                fouls = run = longest = two_strike_run = 0
                reached = set()
                for event in events:
                    count = (event['count']['balls'], event['count']['strikes'])
                    code = event['details']['code']
                    is_foul = code == 'F'
                    reached.add(count)
                    cls.pitches[count] += 1
                    cls.swings[count] += code in ('S', 'F', 'X')
                    cls.foul_pitches[count] += is_foul
                    cls.in_play[count] += code == 'X'
                    if count[1] == 2:
                        cls.after_fouls[two_strike_run] += 1
                        cls.fouls_after_fouls[two_strike_run] += is_foul
                        two_strike_run = two_strike_run + 1 if is_foul else 0
                    else:
                        two_strike_run = 0
                    fouls += is_foul
                    run = run + 1 if is_foul else 0
                    longest = max(longest, run)
                cls.fouls.append(fouls)
                cls.longest.append(longest)
                cls.reached.update(reached)

    def test_at_bat_length_distribution(self):
        # Real: 3.87 pitches/PA; 8.46%, 1.36%, 0.23% reach 7, 9, 11 pitches.
        self.assertTrue(3.7 <= statistics.mean(self.lengths) <= 4.0, statistics.mean(self.lengths))
        for threshold, low, high in ((7, 0.07, 0.10), (9, 0.008, 0.02), (11, 0.001, 0.0045)):
            share = sum(n >= threshold for n in self.lengths) / len(self.lengths)
            with self.subTest(pitches=threshold):
                self.assertTrue(low <= share <= high, share)

    def test_fouls_per_plate_appearance_and_two_strike_pitch(self):
        # Real: 0.72 fouls/PA and 24.2% of pitches with two strikes go foul.
        mean = statistics.mean(self.fouls)
        self.assertTrue(0.65 <= mean <= 0.80, mean)
        rate = sum(n for count, n in self.foul_pitches.items() if count[1] == 2) / sum(
            n for count, n in self.pitches.items() if count[1] == 2)
        self.assertTrue(0.21 <= rate <= 0.28, rate)

    def test_foul_run_distribution_keeps_the_rare_long_battle(self):
        # Real: no fouls in 54.8% of PA; longest run >=2 in 11.7%, >=3 in 2.9%.
        no_fouls = self.longest.count(0) / len(self.longest)
        self.assertTrue(0.51 <= no_fouls <= 0.59, no_fouls)
        for threshold, low, high in ((2, 0.09, 0.14), (3, 0.019, 0.04), (4, 0.003, 0.012)):
            share = sum(n >= threshold for n in self.longest) / len(self.longest)
            with self.subTest(fouls=threshold):
                self.assertTrue(low <= share <= high, share)
        self.assertGreaterEqual(max(self.longest), 6)

    def test_two_strike_fouls_do_not_start_high_then_decay(self):
        # Real: 23.9%, 23.5%, 29.1% after zero, one, two consecutive fouls.
        for run in (0, 1, 2):
            rate = self.fouls_after_fouls[run] / self.after_fouls[run]
            with self.subTest(previous_fouls=run):
                self.assertTrue(0.19 <= rate <= 0.33, rate)

    def test_counts_reached_and_early_swings(self):
        # Real counts reached: 0-2 21.6%, 1-1 37.9%, 1-2 29.0%,
        # 2-2 23.9%, 3-0 3.8%, 3-2 14.0%.
        for count, low, high in (((0, 2), 0.19, 0.24), ((1, 1), 0.35, 0.41),
                                 ((1, 2), 0.26, 0.32), ((2, 2), 0.21, 0.27),
                                 ((3, 0), 0.025, 0.055), ((3, 2), 0.12, 0.16)):
            share = self.reached[count] / len(self.lengths)
            with self.subTest(count=count):
                self.assertTrue(low <= share <= high, share)
        # Real: swing at 32.1% of first pitches and 6.3% of 3-0 pitches;
        # 11.8% of first pitches are put in play.
        for count, low, high in (((0, 0), 0.29, 0.35), ((3, 0), 0.025, 0.10)):
            rate = self.swings[count] / self.pitches[count]
            with self.subTest(swing_count=count):
                self.assertTrue(low <= rate <= high, rate)
        first_in_play = self.in_play[(0, 0)] / self.pitches[(0, 0)]
        self.assertTrue(0.10 <= first_in_play <= 0.13, first_in_play)

    def test_overall_game_calibration(self):
        pa = len(self.lengths)
        for event, low, high in (('strikeout', 0.20, 0.245), ('walk', 0.075, 0.105)):
            share = self.outcomes[event] / pa
            with self.subTest(event=event):
                self.assertTrue(low <= share <= high, share)
        hits = sum(self.outcomes[event] for event in ('single', 'double', 'triple', 'home_run')) / pa
        self.assertTrue(0.19 <= hits <= 0.24, hits)
        self.assertTrue(3.8 <= statistics.mean(self.runs) <= 4.8, statistics.mean(self.runs))


if __name__ == '__main__':
    unittest.main()
