"""Optional sentences: one draw each, measured default rates, no shifted draws."""
from collections import defaultdict
import copy
import json
import math
import re
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
    # "Nomo strikes out the side." and "That's 13 in a row set down by
    # McKeever." are a clean half-inning's outro in place of "Three up, three
    # down": saying one changes the text without always lengthening it.
    REPLACES_THE_OUTRO = {'strikes_out_side', 'retired_in_a_row'}

    def test_every_optional_sentence_is_exercised_and_dropping_it_shifts_no_draw(self):
        offered = set()
        for number in (5, 13, 46, 52):
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
                    if name in self.REPLACES_THE_OUTRO:
                        self.assertNotEqual(said_text, dropped_text)
                    else:
                        self.assertGreater(len(said_text), len(dropped_text))
                    # The other four streams consume exactly the same draws.
                    self.assertEqual(said.positions, baseline.positions)
                    self.assertEqual(dropped.positions, baseline.positions)
        self.assertEqual(offered, set(OPTIONAL_SENTENCE_RATES))

    def test_strikeout_reads_as_a_sentence_with_or_without_the_out(self):
        for number in (5, 46):
            data = episode(number)
            forced = {'strikeout_out_number': True, 'strikeout_inning_end': True}
            said = ForcedRenderer(copy.deepcopy(data), forced).render().splitlines()
            dropped_text = ForcedRenderer(copy.deepcopy(data), {name: False for name in forced}).render()
            dropped = set(dropped_text.splitlines())
            pairs = 0
            for line in said:
                match = re.search(r', (?:for out number (?:one|two|three)|for the (?:first|second|third) out'
                                  r'(?: of the (?:inning|frame))?|to end the (?:inning|ball game))\.$', line)
                if not match:
                    continue
                shorter = line[:match.start()]
                # The dropped form ends the same call cleanly, nothing dangling.
                self.assertTrue(shorter + '.' in dropped or shorter + '!' in dropped
                                or any(candidate in dropped for candidate in
                                       (shorter, shorter.rstrip('.!?') + '.')), line)
                pairs += 1
            self.assertGreater(pairs, 0)
            for line in dropped_text.splitlines():
                if re.search(r'strikes out|down on strikes|strike three', line) and 'TTS' not in line:
                    self.assertRegex(line.rstrip(), r'[.!?]$')

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

    # Home runs are rare in these sleepy broadcasts: the 21 sources hold 33
    # with runs batted in (walk-offs excluded), all of them counted. The
    # sentences below come up once a game or less, so every opportunity in
    # the 21 sources is counted and there are no more to be had.
    MIN_OPPORTUNITIES = {
        'home_run_runs': 30,
        'network_presents': 21, 'host_intro': 21, 'host_back': 21, 'perfect_night': 21, 'crew_chief': 21,
        'final_score': 19, 'pitching_decisions': 19, 'complete_game': 9,
        'new_pitcher_intro': 34, 'new_pitcher_season': 34, 'retired_in_a_row': 28,
        'strikes_out_side': 7, 'steal_throw': 11,
    }
    # Rates deliberately off the measurement, each explained where it is set:
    # the simulator strikes out the side twice as often as the hosts' pitchers
    # did, a rate of one could not be turned off by a fixture's draw, and a
    # recorded throw has no unrecorded opportunities to count.
    SET_BY_HAND = {'strikes_out_side': 0.34, 'perfect_night': 0.97, 'throw_detail': 1.0}
    # The four references record no steal as an event of its own.
    NO_REFERENCE_OPPORTUNITIES = {'steal_throw'}

    def test_rates_match_the_source_measurement(self):
        measured = {row['gate']: row for row in measure()}
        self.assertEqual(set(measured) | {'throw_detail'}, set(OPTIONAL_SENTENCE_RATES))
        for name, rate in OPTIONAL_SENTENCE_RATES.items():
            with self.subTest(name=name):
                if name == 'throw_detail':
                    self.assertEqual(rate, self.SET_BY_HAND[name])
                    continue
                row = measured[name]
                self.assertGreaterEqual(row['opportunities'], self.MIN_OPPORTUNITIES.get(name, 80))
                if name not in self.NO_REFERENCE_OPPORTUNITIES:
                    self.assertGreater(row['reference'][1], 0, 'PBP references contribute opportunities')
                if name in self.SET_BY_HAND:
                    self.assertEqual(rate, self.SET_BY_HAND[name])
                else:
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
                if name == 'new_pitcher_season':
                    # A simulated boxscore has no season statistics to read.
                    self.assertEqual(values, [])
                    continue
                if name == 'complete_game' and not values:
                    # No starter goes nine in these ten games.
                    continue
                # Once a game or less: ten games ask ten times, or fewer.
                self.assertGreaterEqual(len(values), 1 if name in self.MIN_OPPORTUNITIES
                                        or name in self.SET_BY_HAND else 20)
                tolerance = 4 * math.sqrt(rate * (1 - rate) / len(values)) + 0.02
                self.assertAlmostEqual(sum(values) / len(values), rate, delta=tolerance)


if __name__ == '__main__':
    unittest.main()
