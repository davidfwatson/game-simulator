"""Regression coverage for explicit commentary randomness and legacy replay."""
import copy
import json
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile

from renderers.base import GameRenderer
from renderers.narrative.renderer import NarrativeRenderer
from renderers.randomness import ChoiceRNG


class TestCommentaryRandomness(unittest.TestCase):
    def setUp(self):
        self.data = {'gameData': {'teams': {'home': {}, 'away': {}}}}

    def test_draws_are_independent_and_support_large_pools(self):
        draws = [121, 18, 202, 99, 320]
        rng = ChoiceRNG(draws, seed=42)
        pool = list(range(400))
        self.assertEqual([rng.choice(pool) for _ in draws], draws)
        self.assertEqual(draws, [121, 18, 202, 99, 320])
        self.assertEqual(ChoiceRNG([73], 0).random(), .73)

    def test_exhausted_tapes_continue_with_reproducible_variation(self):
        def sample():
            rng = ChoiceRNG([7], 42)
            return [rng.choice(range(1000)) for _ in range(40)]
        actual = sample()
        self.assertEqual(actual, sample())
        self.assertEqual(actual[0], 7)
        self.assertGreater(len(set(actual[1:])), 20)

    def test_overrides_do_not_shift_fallback(self):
        original = ChoiceRNG([], 123)
        edited = ChoiceRNG([0, 0, 0], 123)
        for _ in range(3):
            original.choice(range(8))
            edited.choice(range(8))
        self.assertEqual([original.random() for _ in range(10)],
                         [edited.random() for _ in range(10)])

    def test_invalid_metadata_fails_clearly(self):
        for value in (None, {}, [-1], [True], [1.5], ['3']):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ChoiceRNG(value, 0)
        renderer = GameRenderer(self.data)
        with self.assertRaisesRegex(ValueError, 'Invalid commentary streams'):
            renderer._reseed_for_point({'commentaryRng': {'event': {'typo': []}}},
                                       'event', '', 'event:0')

    def test_streams_and_clock_are_independent(self):
        renderer = GameRenderer(self.data, seed=99)
        owner = {'commentaryRng': {'event': {'play': [3, 4, 5], 'pitch': [73]}}}
        def sample(timestamp):
            renderer._reseed_for_point(owner, 'event', timestamp, 'play:0:event:0')
            return [renderer.rng_play.choice(range(500)) for _ in range(10)]
        before = sample('2025-01-01T00:00:00Z')
        self.assertEqual(before, sample('2030-12-31T23:59:59.123Z'))
        owner['commentaryRng']['event']['pitch'] = [22, 99, 101]
        self.assertEqual(before, sample(''))
        self.assertIs(renderer.rng, renderer.rng_play)

    def test_partial_adoption_can_return_to_normal_rng(self):
        renderer = GameRenderer(self.data, seed=42)
        renderer._reseed_for_point({'commentaryRng': {'event': {'play': [5]}}},
                                   'event', '', 'play:0:event:0')
        renderer._reseed_for_point({}, 'event', '2025-01-01T00:00:00Z', 'play:0:event:1')
        self.assertIsInstance(renderer.rng_play.choice(['a', 'b']), str)

    def test_unannotated_points_also_ignore_clock(self):
        renderer = GameRenderer(self.data, seed=42)
        def sample(timestamp):
            renderer._reseed_for_point({}, 'event', timestamp, 'play:0:event:1')
            return [renderer.rng_play.random() for _ in range(10)]
        self.assertEqual(sample('2025-01-01T00:00:00Z'), sample(''))

    def test_persisted_seed_replays_and_zero_overrides_it(self):
        self.data['gameData']['commentarySeed'] = 99
        def sample(seed=None):
            renderer = GameRenderer(self.data, seed=seed)
            return [renderer.rng_color.random() for _ in range(5)]
        self.assertEqual(sample(), sample(99))
        self.assertNotEqual(sample(), sample(0))

    def test_example_json_roundtrip_preserves_explicit_zero_seed(self):
        from example_games import ExampleGame
        from renderers.statcast import StatcastRenderer
        example = ExampleGame(game_seed=1, commentary_seed=0)
        data = json.loads(example.render('gameday'))
        self.assertEqual(data['gameData']['commentarySeed'], 0)
        self.assertEqual(NarrativeRenderer(data).render(), example.render())
        self.assertEqual(StatcastRenderer(data).render(), example.render('statcast'))

    def test_cli_exports_effective_seed_and_loaded_games(self):
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory() as tmp:
            gameday = Path(tmp) / 'game.json'
            pbp = Path(tmp) / 'game.txt'
            subprocess.run([sys.executable, str(root / 'baseball.py'),
                            '--game-seed', '1', '--commentary-seed', '0',
                            '--max-innings', '1', '--gameday-outfile', str(gameday),
                            '--pbp-outfile', str(pbp)], check=True, capture_output=True)
            data = json.loads(gameday.read_text())
            self.assertEqual(data['gameData']['commentarySeed'], 0)
            self.assertEqual(NarrativeRenderer(data).render(), pbp.read_text())
            loaded = subprocess.run([sys.executable, str(root / 'baseball.py'),
                                     '--gameday-file', str(gameday),
                                     '--commentary-seed', '12', '--commentary', 'gameday'],
                                    check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(loaded.stdout)['gameData']['commentarySeed'], 12)

    def test_renderer_instances_can_be_reused(self):
        from renderers.statcast import StatcastRenderer
        path = Path(__file__).parent / 'test_fixture_pbp_example_1.json'
        data = json.loads(path.read_text())
        for renderer in (NarrativeRenderer(data), NarrativeRenderer(data, verbose=False),
                         StatcastRenderer(data)):
            with self.subTest(renderer=type(renderer).__name__):
                self.assertEqual(renderer.render(), renderer.render())

    def test_fixture_replay_ignores_timestamp_edits(self):
        path = Path(__file__).parent / 'test_fixture_pbp_example_1.json'
        data = json.loads(path.read_text())
        original = copy.deepcopy(data)
        expected = NarrativeRenderer(data).render()
        self.assertEqual(data, original)
        data['gameData']['datetime']['dateTime'] = '2030-01-01T00:00:00Z'
        for play in data['liveData']['plays']['allPlays']:
            play['about']['startTime'] = '2030-01-01T00:00:00Z'
            play['about']['endTime'] = '2030-01-01T01:00:00Z'
            for event in play['playEvents']:
                event['startTime'] = '2030-01-01T00:30:00Z'
        self.assertEqual(NarrativeRenderer(data).render(), expected)
        self.assertEqual(NarrativeRenderer(original).render(), expected)


if __name__ == '__main__':
    unittest.main()
