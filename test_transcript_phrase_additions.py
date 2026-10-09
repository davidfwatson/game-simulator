"""Source-backed vocabulary audited for provenance, formatting, and pitch replay.

These tests cover each reusable phrase, not reconstructed game similarity.
Integer pool indices select the actual renderer helper's choices; no RNG or
phrase selector is mocked, and the source catalog is never used by production.
"""

import copy
import json
from pathlib import Path
import re
import string
import unittest

from renderers.narrative.renderer import NarrativeRenderer
from renderers.randomness import ChoiceRNG, STREAM_NAMES
from transcript_comparison import contains_phrase, get_pool, normalized_words


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / 'transcripts' / 'sleep_baseball'
CONNECTORS = {'pitch_connectors_00', 'pitch_connectors', 'payoff_pitch'}
FORMAT_FIELDS = {'pitcher_name_last', 'batter_name_last', 'count_str',
                 'count_str_and', 'count_str_cap', 'count_str_and_cap'}


def connector_inputs(row):
    """Recover the source names/count from a reviewed reusable connector."""
    key = row['pool'].split('.')[-1]
    inputs = {'balls': 0 if key == 'pitch_connectors_00' else 1,
              'strikes': 0 if key == 'pitch_connectors_00' else 1,
              'pitcher_name': 'Sample Pitcher', 'batter_name': 'Example Batter',
              'runners_on_base': False}
    if key == 'payoff_pitch':
        inputs.update(balls=3, strikes=2)
    pattern = []
    for literal, field, _, _ in string.Formatter().parse(row['template']):
        pattern.extend(re.escape(word) for word in normalized_words(literal))
        if field:
            if field not in FORMAT_FIELDS:
                raise ValueError(f'Unsupported connector field {field}')
            pattern.append(f'(?P<{field}>.+?)')
    match = re.fullmatch(r'\s+'.join(pattern), ' '.join(normalized_words(row['expected'])))
    if not match:
        raise ValueError(f'Connector does not match its source phrase: {row}')
    for field, value in match.groupdict().items():
        if field == 'pitcher_name_last':
            inputs['pitcher_name'] = 'Source ' + value
        elif field == 'batter_name_last':
            inputs['batter_name'] = 'Source ' + value
        elif field.startswith('count_str'):
            words = [word for word in value.split() if word != 'and']
            numbers = {'oh': 0, 'zero': 0, 'one': 1, 'two': 2, 'three': 3}
            inputs.update(balls=numbers[words[0]], strikes=numbers[words[-1]])
    return inputs


def replay_helper(row, timestamp='', location=None):
    renderer = NarrativeRenderer({'gameData': {'commentarySeed': 31, 'teams': {
        'home': {'name': 'Home Team'}, 'away': {'name': 'Away Team'},
    }}, 'liveData': {'plays': {'allPlays': []}}})
    key = row['pool'].split('.')[-1]
    stream = 'flow' if key in CONNECTORS else 'pitch'
    draws = {name: [] for name in STREAM_NAMES}
    draws[stream] = [get_pool(row['pool']).index(row['template'])]
    owner = {'commentaryRng': {'case': draws}}
    before = copy.deepcopy(owner)
    renderer._reseed_for_point(owner, 'case', timestamp, 'source-phrase')
    if row['pool'].startswith('pitch_locations.ball.') or row['pool'].startswith('pitch_locations.strike.'):
        code = 'B' if '.ball.' in row['pool'] else 'C'
        text = renderer._get_pitch_description_for_location(
            code, None, 'fastball', 'R', location or row['location'])
    elif row['pool'] == 'pitch_locations.foul':
        text = renderer._get_foul_description()
    elif key in CONNECTORS:
        text = renderer._get_pitch_connector(**connector_inputs(row))
    else:
        text = renderer._get_narrative_string(key, rng=renderer.rng_pitch)
    return text, renderer, stream, owner, before


class EventStreamsRenderer(NarrativeRenderer):
    """Observe the real event streams without replacing their behavior."""
    def _reseed_for_point(self, owner, point, timestamp, key):
        super()._reseed_for_point(owner, point, timestamp, key)
        if point == 'event':
            self.observed_event_streams = {name: getattr(self, 'rng_' + name)
                                           for name in STREAM_NAMES}


class TestTranscriptPitchAdditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / 'transcript_pitch_additions.json').read_text())
        cls.sources = {int(path.stem[8:]): path.read_text().splitlines()
                       for path in SOURCE_DIR.glob('episode_*.txt')}
        # Use the existing roster/venue scaffold, then replace its plays with
        # one controlled pitch. No corpus snapshot or fitted RNG is required.
        scaffold = json.loads((ROOT / 'test_fixture_pbp_example_1.json').read_text())
        scaffold['liveData']['plays']['allPlays'] = scaffold['liveData']['plays']['allPlays'][:1]
        scaffold['gameData']['broadcast'] = {'complete': False, 'strictFacts': True}
        cls.scaffold = scaffold

    def test_every_catalog_entry_has_real_source_and_unique_supported_template(self):
        self.assertEqual({row['episode'] for row in self.rows}, set(self.sources))
        seen = set()
        for row in self.rows:
            with self.subTest(episode=row['episode'], line=row['line'], pool=row['pool']):
                self.assertIs(type(row['line']), int)
                self.assertGreater(row['line'], 0)
                source = self.sources[row['episode']][row['line'] - 1]
                self.assertTrue(contains_phrase(source, row['expected']))
                key = (row['pool'], tuple(normalized_words(row['template'])))
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertEqual(get_pool(row['pool']).count(row['template']), 1)
                fields = {field for _, field, _, _ in string.Formatter().parse(row['template']) if field}
                self.assertLessEqual(fields, FORMAT_FIELDS)
                if row['pool'].startswith('pitch_locations.'):
                    self.assertFalse(fields)
                if row.get('requires'):
                    self.assertIn(row['requires'], {'ball_location', 'called_strike_location'})
                    self.assertTrue(row['pool'].endswith('.' + row['location']))

    def test_all_phrases_replay_through_real_helpers_and_explicit_streams(self):
        for row in self.rows:
            with self.subTest(episode=row['episode'], line=row['line'], template=row['template']):
                text, renderer, selected, owner, before = replay_helper(row)
                self.assertTrue(contains_phrase(text, row['expected']), text)
                for stream in STREAM_NAMES:
                    rng = getattr(renderer, 'rng_' + stream)
                    self.assertIsInstance(rng, ChoiceRNG)
                    self.assertEqual(rng.position, int(stream == selected))
                self.assertEqual(owner, before)
                self.assertEqual(text, replay_helper(row, '2099-01-01T00:00:00Z')[0])

    def _render_pitch(self, row, location=None):
        data = copy.deepcopy(self.scaffold)
        play = data['liveData']['plays']['allPlays'][0]
        key = row['pool'].split('.')[-1]
        code = 'B' if '.ball.' in row['pool'] else 'C'
        strikes = 0
        if row['pool'] == 'pitch_locations.foul' or key == 'bunt_foul':
            code = 'F'
        elif key.startswith('strike_swinging'):
            code = 'S'
        if key.endswith('_three'):
            strikes = 2
        elif key.endswith('_two'):
            strikes = 1
        event = {
            'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': strikes},
            'details': {'code': code, 'description': 'Bunt foul' if key == 'bunt_foul' else 'Pitch',
                        'type': {'description': 'Fastball'}, 'isStrike': code != 'B'},
            'commentaryRng': {'event': {name: [] for name in STREAM_NAMES}},
        }
        event['commentaryRng']['event']['pitch'] = [get_pool(row['pool']).index(row['template'])]
        event['commentaryRng']['event']['flow'] = [0, 99, 99, 99]
        if row.get('location'):
            event['details']['location'] = location or row['location']
        play['playEvents'] = [event]
        play['result'].update(event='Incomplete', eventType='incomplete')
        play['about']['isComplete'] = False
        play['runners'] = []
        play['count'] = {'balls': int(code == 'B'), 'strikes': strikes + int(code != 'B'), 'outs': 0}
        renderer = EventStreamsRenderer(data)
        text = renderer.render()
        self.assertIsInstance(renderer.observed_event_streams['pitch'], ChoiceRNG)
        self.assertEqual(renderer.observed_event_streams['pitch'].position, 1)
        return text

    def test_pitch_event_dispatch_reaches_every_location_foul_and_strike_phrase(self):
        for row in self.rows:
            if row['pool'].split('.')[-1] in CONNECTORS:
                continue
            with self.subTest(pool=row['pool'], template=row['template']):
                self.assertTrue(contains_phrase(self._render_pitch(row), row['expected']))

    def test_wrong_semantic_location_does_not_replay_the_source_phrase(self):
        for pool, other in [('pitch_locations.ball.high', 'low'),
                            ('pitch_locations.strike.outside_corner', 'middle')]:
            row = next(row for row in self.rows if row['pool'] == pool)
            with self.subTest(pool=pool):
                self.assertFalse(contains_phrase(replay_helper(row, location=other)[0], row['expected']))
                self.assertFalse(contains_phrase(self._render_pitch(row, location=other), row['expected']))


class TestTranscriptPlayAdditions(unittest.TestCase):
    # These are the formatting contexts supplied by NarrativeRenderer.render()
    # and play_description.generate_play_description/get_runner_status_string.
    # Keep route-specific sets: a valid outcome variable need not be available
    # to a batter introduction, walk, strikeout, or inning transition.
    OUTCOME_FIELDS = {
        'batter_name', 'batter_last_name', 'direction', 'direction_noun',
        'pitch_type', 'pitch_type_lower', 'pitch_velo', 'fielder_name',
        'result_outs', 'result_outs_word', 'out_context_str', 'dp_notation',
    }
    STRIKEOUT_FIELDS = {
        'batter_name', 'pitch_type', 'out_context_str', 'result_outs_word',
        'result_outs', 'batter_last_name',
    }
    WALK_FIELDS = {'last_pitch_context', 'batter_name', 'outs_str'}
    INNING_FIELDS = {
        'inning_ordinal', 'inning_count_word', 'away_team_name', 'home_team_name',
        'away_short', 'home_short', 'score_away', 'score_home', 'leading_team',
        'trailing_team', 'leading_short', 'trailing_short', 'score_lead',
        'leading_score_val', 'score_trail', 'score', 'location', 'location_with_state', 'venue',
        'innings_word', 'batting_team', 'fielding_team', 'batting_team_short',
        'fielding_team_short', 'pitcher_name', 'hits_str', 'lob_str',
        'runs_scored_word', 'runs_scored_str', 'score_str', 'score_recap',
        'next_inning_ordinal', 'network_name', 'station_call', 'score_context',
        'consecutive_retired',
    }
    INNING_INTRO_FIELDS = {
        'half', 'half_lower', 'inning_ordinal', 'venue', 'location', 'location_with_state',
        'score_str', 'score_context', 'score_phrase', 'batting_team',
        'batting_team_short', 'due_up_desc', 'pitcher_name', 'weather_desc',
    }

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / 'transcript_play_additions.json').read_text())
        cls.sources = {int(path.stem[8:]): path.read_text().splitlines()
                       for path in SOURCE_DIR.glob('episode_*.txt')}

    def supported_fields(self, pool):
        if pool.startswith('narrative_templates.Strikeout.'):
            return self.STRIKEOUT_FIELDS
        if pool.startswith('narrative_templates.Walk.'):
            return self.WALK_FIELDS
        if pool.startswith('narrative_templates.Hit By Pitch.'):
            return {'batter_name'}
        if pool.startswith('narrative_templates.'):
            return self.OUTCOME_FIELDS
        key = pool.split('.')[-1]
        if pool.startswith('radio_strings.'):
            if key in ('inning_break_intro_bottom', 'inning_break_intro_top'):
                return self.INNING_INTRO_FIELDS
            if key.startswith('inning_'):
                return self.INNING_FIELDS
            if key == 'outro':
                return {'win_team', 'win_runs', 'win_hits', 'win_errors',
                        'lose_team', 'lose_runs', 'lose_hits', 'lose_errors',
                        'network_name'}
            if key == 'welcome_intro':
                return set()  # No formatting fields in the current additions.
        if pool.startswith('narrative_strings.'):
            if key == 'batter_intro_runners':
                return {'batter_name', 'runners_str', 'outs_str', 'pitcher_name'}
            if key in ('batter_intro_empty', 'batter_intro_leadoff', 'batter_intro_bases_cleared'):
                return {'batter_name', 'team_name', 'outs_str', 'position', 'pitcher_name'}
            if key in ('batter_intro_pitcher', 'batter_intro_cleanup',
                       'batter_intro_winning_run', 'batter_intro_winning_run_first',
                       'intentional_walk', 'intentional_walk_pitcher_next'):
                return {'batter_name'}
            if key == 'inning_end_123_relief':
                return {'pitcher_name', 'inning_ordinal'}
            if key in ('leadoff_walk_four_pitch', 'walk_forces_run'):
                return self.WALK_FIELDS
            if key in ('double_one_out', 'leadoff_double', 'leadoff_walk',
                       'two_out_double', 'two_out_walk'):
                return {'batter_name', 'inning_context'}
            if key.startswith('pinch_hitter'):
                return {'batter_name', 'replaced', 'slot', 'outs_lead', 'outs_count'}
            if key in ('runner_scores', 'runner_to_third'):
                return {'runner', 'origin'}
            if key.startswith('rbi_hit'):
                return {'batter_name', 'hit', 'runs'}
            if key.startswith('home_run_'):
                return {'batter_name'}
        if pool.startswith('lineup_strings.season_'):
            return {'last_name', 'wins', 'losses', 'era', 'wins_word', 'losses_word'}
        self.fail(f'No reviewed production formatting context for {pool}')

    def test_all_231_play_entries_retain_exact_source_provenance_and_pool_membership(self):
        # 178 from the source-mining pass, then 53 phrasings of newly recorded
        # facts (pinch hitters, season records, runners who score, RBIs).
        self.assertEqual(len(self.rows), 231)
        self.assertEqual({row['episode'] for row in self.rows}, set(self.sources))
        seen = set()
        for row in self.rows:
            with self.subTest(episode=row['episode'], line=row['line'], pool=row['pool']):
                self.assertIs(type(row['line']), int)
                self.assertGreater(row['line'], 0)
                source = self.sources[row['episode']][row['line'] - 1]
                self.assertEqual(source, row['source_text'])
                self.assertTrue(contains_phrase(source, row['expected']))
                key = (row['pool'], tuple(normalized_words(row['template'])))
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertEqual(get_pool(row['pool']).count(row['template']), 1)

    def test_all_play_template_fields_belong_to_their_production_context(self):
        for row in self.rows:
            with self.subTest(pool=row['pool'], template=row['template']):
                fields = {field for _, field, _, _ in string.Formatter().parse(row['template']) if field}
                supported = self.supported_fields(row['pool'])
                self.assertLessEqual(fields, supported)
                # Formatting also validates braces/conversions. Do not build
                # this context from the template's own fields: that would hide
                # variables which the real caller never supplies.
                rendered = row['template'].format(**{field: 'Example' for field in supported})
                self.assertNotIn('{', rendered)
                self.assertNotIn('}', rendered)


if __name__ == '__main__':
    unittest.main()
