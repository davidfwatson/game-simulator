"""The hosts' wording added by frequency: provenance, weights and no new tells.

``wording_additions.py`` measures every added template against the sources.
These tests keep the catalog, the production pools and ``TEMPLATE_WEIGHTS``
in step, check each template's slots against the context its route supplies,
and check that simulated games draw each template about as often as the hosts
said it.
"""
import json
import random
import re
import string
import unittest
from collections import Counter
from pathlib import Path

from commentary import GAME_CONTEXT, TEMPLATE_WEIGHTS, WORDING_ADDITIONS, WORDING_NEW_POOLS
from renderers.randomness import ChoiceRNG, template_weights
from transcript_comparison import get_pool
import wording_additions

ROOT = Path(__file__).resolve().parent

# The formatting context each route supplies (see NarrativeRenderer.render).
INTRO = {'half', 'half_lower', 'inning_ordinal', 'venue', 'location', 'location_with_state', 'score_str',
         'score_context', 'score_phrase', 'batting_team', 'batting_team_short', 'due_up_desc', 'pitcher_name',
         'weather_desc', 'network_name', 'station_call', 'score_lead'}
SUMMARY = {'inning_ordinal', 'inning_count_word', 'away_team_name', 'home_team_name', 'away_short', 'home_short',
           'score_away', 'score_home', 'leading_team', 'trailing_team', 'leading_short', 'trailing_short',
           'score_lead', 'leading_score_val', 'score_trail', 'score', 'location', 'location_with_state', 'venue',
           'innings_word', 'batting_team', 'fielding_team', 'batting_team_short', 'fielding_team_short',
           'pitcher_name', 'hits_str', 'lob_str', 'runs_scored_word', 'runs_scored_str', 'score_str',
           'score_recap', 'next_inning_ordinal', 'network_name', 'station_call', 'consecutive_retired'}
FIELDS = {
    'radio_strings.inning_break_return': INTRO,
    'radio_strings.inning_break_intro_top': INTRO,
    'radio_strings.inning_break_intro_bottom': INTRO,
    'radio_strings.station_intro': {'network_name', 'station_call'},
    'radio_strings.outro': {'win_team', 'win_runs', 'win_hits', 'win_errors', 'lose_team', 'lose_runs',
                            'lose_hits', 'lose_errors', 'network_name', 'station_call'},
    'narrative_strings.batter_intro_leadoff': {'batter_name', 'team_name', 'team_short', 'team_short_possessive',
                                               'outs_str', 'position', 'pitcher_name'},
    'narrative_strings.batter_intro_empty': {'batter_name', 'team_name', 'team_short', 'team_short_possessive',
                                             'outs_str', 'position', 'pitcher_name'},
    'narrative_strings.count_full': set(),
    'narrative_strings.count_even': {'count_str', 'pitcher_name_last', 'batter_name'},
    'narrative_strings.count_plain': {'count_str', 'pitcher_name_last', 'batter_name'},
}
PITCH_FIELDS = {'pitch_type', 'pitch_type_lower', 'pitch_type_short', 'pitch_type_family', 'strike_call',
                'strike_number_word', 'ball_number_word', 'ball_call'}


def fields(template):
    return {field for _, field, _, _ in string.Formatter().parse(template) if field}


def supported(pool):
    if pool in FIELDS:
        return FIELDS[pool]
    if pool.startswith('radio_strings.inning_'):
        return SUMMARY
    if pool.startswith('pitch_locations.'):
        return PITCH_FIELDS
    return set()   # outs, out context and foul phrases are plain strings


class TestWordingCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(wording_additions.CATALOG.read_text())
        cls.sources = {}
        for game in wording_additions.games():
            cls.sources[game.stem] = game.raw

    def test_catalog_lists_every_added_template_once(self):
        added = []
        for pool, templates in WORDING_ADDITIONS.items():
            # A new pool's first entry is the phrase the renderer said before.
            added += [(pool, t) for t in (templates[1:] if pool in WORDING_NEW_POOLS else templates)]
        self.assertEqual(sorted(added), sorted((row['pool'], row['template']) for row in self.rows))
        for pool, template in added:
            self.assertEqual(get_pool(pool).count(template), 1, (pool, template))

    def test_catalog_is_current_with_the_sources(self):
        self.assertEqual(wording_additions.build(), self.rows)

    def test_weights_are_the_catalogs(self):
        self.assertEqual(TEMPLATE_WEIGHTS, wording_additions.weights(self.rows))

    def test_provenance_is_exact_and_each_phrasing_recurs(self):
        for row in self.rows:
            with self.subTest(template=row['template']):
                self.assertTrue(row['provenance'])
                self.assertGreater(row['said'], 0)
                # One-episode phrasings only when plain broadcast language.
                self.assertTrue(len(row['episodes']) >= 2 or row['generic'])
                for cite in row['provenance']:
                    line = self.sources[cite['source']][cite['line'] - 1]
                    self.assertEqual(line, cite['source_text'])
                    self.assertIn(cite['expected'].casefold(), line.casefold())

    def test_template_slots_belong_to_their_route(self):
        for pool, templates in WORDING_ADDITIONS.items():
            for template in templates:
                with self.subTest(pool=pool, template=template):
                    self.assertLessEqual(fields(template), supported(pool))
                    rendered = template.format(**{field: 'Example' for field in supported(pool)})
                    self.assertNotIn('{', rendered)

    def test_weights_draw_each_template_at_the_hosts_rate(self):
        by_pool = {}
        for row in self.rows:
            by_pool.setdefault(row['pool'], []).append(row)
        for pool, members in by_pool.items():
            original = members[0]['original_pool_size']
            total = original + sum(TEMPLATE_WEIGHTS[r['template']] for r in members)
            share = sum(r['rate'] for r in members)
            for row in members:
                with self.subTest(template=row['template']):
                    probability = TEMPLATE_WEIGHTS[row['template']] / total
                    expected = row['rate'] * min(1.0, wording_additions.MAX_SHARE / share)
                    self.assertAlmostEqual(probability, max(expected, 0.0005 * original / total), delta=0.01)


class TestWeightedChoice(unittest.TestCase):
    def test_explicit_draws_ignore_weights_and_fallback_follows_them(self):
        pool = ['plain', 'And that {pitch_type_lower} misses low']
        self.assertIsNotNone(template_weights(pool))
        self.assertIsNone(template_weights(['plain', 'other']))
        explicit = ChoiceRNG([1, 0], seed=3)
        self.assertEqual([explicit.choice(pool), explicit.choice(pool)], pool[::-1])
        rng = ChoiceRNG([], seed=7)
        counts = Counter(rng.choice(pool) for _ in range(4000))
        weight = TEMPLATE_WEIGHTS[pool[1]]
        self.assertAlmostEqual(counts[pool[1]] / 4000, weight / (1 + weight), delta=0.03)

    def test_unweighted_pools_draw_exactly_as_before(self):
        pool = ['a b', 'c d', 'e f']
        rng, reference = ChoiceRNG([], seed=11), random.Random(11)
        self.assertEqual([rng.choice(pool) for _ in range(50)], [reference.choice(pool) for _ in range(50)])


class TestSpokenValues(unittest.TestCase):
    """Value fixes measured in the sources, checked on simulated games."""

    @classmethod
    def setUpClass(cls):
        from example_games import EXAMPLE_GAMES
        cls.games = [game.render() for game in EXAMPLE_GAMES[:4]]

    def test_network_takes_its_article_once(self):
        from renderers.narrative.renderer import NarrativeRenderer
        self.assertEqual(NarrativeRenderer._network_with_article('Northwoods Baseball Radio Network'),
                         'the Northwoods Baseball Radio Network')
        self.assertEqual(NarrativeRenderer._network_with_article('The Pacific Sleep Baseball Network'),
                         'the Pacific Sleep Baseball Network')
        for text in self.games:
            self.assertNotRegex(text, r'\b[Tt]he [Tt]he\b')
            self.assertNotRegex(text, r'(?:on|and) Pacific Sleep')

    def test_break_scores_and_innings_are_spoken_correctly(self):
        for text in self.games:
            summaries = [line for line in text.splitlines() if "We'll be back" in line or 'be right back' in line]
            self.assertTrue(summaries)
            for line in summaries:
                self.assertNotRegex(line, r'\b(?:[A-Z][a-z]+) \d+, ')       # "Tigers 2, Ravens 1"
                self.assertNotIn('and a half in the books', line)
                self.assertNotIn('zero in the books', line)
            self.assertNotRegex(text, r'will bring the \d')

    def test_half_innings_count_from_the_right_side_of_the_break(self):
        from renderers.narrative.renderer import NarrativeRenderer
        self.assertEqual(NarrativeRenderer._get_innings_word(NarrativeRenderer.__new__(NarrativeRenderer), 0, 'Bottom'),
                         'a half')
        for text in self.games:
            lines = text.splitlines()
            for index, line in enumerate(lines):
                match = re.search(r'\bafter (one|two|three|four|five|six|seven|eight)( and a half)?\b', line)
                if not match or "be back" not in line:
                    continue
                # The next half-inning header says which break this was.
                following = next((l for l in lines[index + 1:index + 5] if re.search(r'\b(?:Top|Bottom|top|bottom) (?:half )?of the', l)), '')
                if not following:
                    continue
                if match.group(2):
                    self.assertRegex(following, r'[Bb]ottom', line)
                else:
                    self.assertRegex(following, r'[Tt]op', line)


class TestFitterSlots(unittest.TestCase):
    def test_a_slot_is_a_gap_not_a_dropped_word(self):
        from fit_transcript_games import option_score, tokens
        window = tokens('The one-oh pitch... Fouled back and out of play.')
        self.assertGreater(option_score('The {count_str} pitch...', window),
                           option_score('The {count_str}...', window))


class TestSimulatedRepetition(unittest.TestCase):
    def test_added_templates_recur_no_more_than_the_hosts_said_them(self):
        import template_repetition
        summary = template_repetition.summarize(template_repetition.record_games(30))
        self.assertEqual(template_repetition.check(summary), [])


if __name__ == '__main__':
    unittest.main()
