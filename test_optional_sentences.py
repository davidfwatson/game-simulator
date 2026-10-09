"""Optional sentences: one draw each, measured default rates, no shifted draws."""
from collections import defaultdict
import copy
import json
import math
import unittest

from example_games import EXAMPLE_GAMES
from baseball import BaseballSimulator
from optional_sentence_rates import measure
from renderers import NarrativeRenderer
from renderers.narrative.renderer import OPTIONAL_SENTENCE_RATES
from renderers.randomness import STREAM_NAMES
from transcript_game_fixtures import OUTPUT_DIR


def episode(number):
    return json.loads((OUTPUT_DIR / f'episode_{number:03d}.json').read_text())


class ForcedRenderer(NarrativeRenderer):
    """Say (or drop) every optional sentence of one kind; log stream use."""

    def __init__(self, data, forced=None):
        self.forced, self.asked, self.positions = forced or {}, defaultdict(list), {}
        self._point = None
        super().__init__(data)

    def _optional(self, name):
        said = super()._optional(name)
        said = self.forced.get(name, said)
        self.asked[name].append(said)
        return said

    def _log(self):
        if self._point is not None:
            self.positions[self._point] = tuple(
                getattr(self, f'rng_{name}').position for name in STREAM_NAMES if name != 'optional')

    def _reseed_for_point(self, owner, point, timestamp, key):
        self._log()
        super()._reseed_for_point(owner, point, timestamp, key)
        self._point = key

    def render(self):
        text = super().render()
        self._log()
        return text


class TestOptionalSentences(unittest.TestCase):
    def test_every_optional_sentence_is_exercised_and_dropping_it_shifts_no_draw(self):
        offered = set()
        for number in (5, 13, 46):
            data = episode(number)
            baseline = ForcedRenderer(copy.deepcopy(data))
            self.assertEqual(baseline.render(), NarrativeRenderer(copy.deepcopy(data)).render())
            for name in OPTIONAL_SENTENCE_RATES:
                with self.subTest(episode=number, name=name):
                    said = ForcedRenderer(copy.deepcopy(data), {name: True})
                    dropped = ForcedRenderer(copy.deepcopy(data), {name: False})
                    said_text, dropped_text = said.render(), dropped.render()
                    if not said.asked[name]:
                        continue
                    offered.add(name)
                    self.assertGreater(len(said_text), len(dropped_text))
                    # The other four streams consume exactly the same draws.
                    self.assertEqual(said.positions, baseline.positions)
                    self.assertEqual(dropped.positions, baseline.positions)
        self.assertEqual(offered, set(OPTIONAL_SENTENCE_RATES))

    def test_count_after_a_numbered_call_is_optional(self):
        data = episode(5)
        said = ForcedRenderer(copy.deepcopy(data), {'count_after_numbered_call': True}).render()
        dropped = ForcedRenderer(copy.deepcopy(data), {'count_after_numbered_call': False}).render()
        pattern = r'for ball two[.,] (?:It\'s )?[Tt]wo and (?:oh|one|two)\.'
        self.assertRegex(said, pattern)
        self.assertNotRegex(dropped, pattern)

    def test_optional_draws_are_integers_on_their_own_stream(self):
        for number in (5, 46):
            data = episode(number)
            draws = [point['optional'] for play in data['liveData']['plays']['allPlays']
                     for owner in [play] + play['playEvents']
                     for point in owner.get('commentaryRng', {}).values()]
            values = [value for stream in draws for value in stream]
            self.assertTrue(values)
            self.assertTrue(all(type(value) is int and 0 <= value < 100 for value in values))

    def test_rates_match_the_source_measurement(self):
        measured = {row['gate']: row for row in measure()}
        self.assertEqual(set(measured), set(OPTIONAL_SENTENCE_RATES))
        for name, rate in OPTIONAL_SENTENCE_RATES.items():
            with self.subTest(name=name):
                row = measured[name]
                self.assertGreaterEqual(row['opportunities'], 80)
                self.assertGreater(row['reference'][1], 0, 'PBP references contribute opportunities')
                self.assertAlmostEqual(rate, row['rate'], delta=0.006)

    def test_simulated_games_say_optional_sentences_at_the_measured_rate(self):
        asked = defaultdict(list)
        for game in EXAMPLE_GAMES:
            simulator = BaseballSimulator(game.team1, game.team2, game_seed=game.game_seed)
            simulator.play_game()
            renderer = ForcedRenderer(simulator.gameday_data, {})
            renderer.render()
            for name, values in renderer.asked.items():
                asked[name].extend(values)
        for name, rate in OPTIONAL_SENTENCE_RATES.items():
            with self.subTest(name=name):
                values = asked[name]
                self.assertGreaterEqual(len(values), 20)
                tolerance = 4 * math.sqrt(rate * (1 - rate) / len(values)) + 0.02
                self.assertAlmostEqual(sum(values) / len(values), rate, delta=tolerance)


if __name__ == '__main__':
    unittest.main()
