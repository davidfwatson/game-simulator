"""Real corpus replay plus failures that superficial phrase matching would miss."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from renderers.randomness import ChoiceRNG, STREAM_NAMES
import transcript_comparison as comparison
from update_transcript_examples import update_examples
from pbp_comparison import check_transcript_examples, validate_transcript_counts


class TestTranscriptCompilation(unittest.TestCase):
    def setUp(self):
        self.source_lines = ['The ball is high and tight.']
        self.case = {
            'id': 'inside-fastball', 'source_line': 1,
            'source_text': self.source_lines[0], 'expected': 'high and tight',
            'kind': 'pitch_location', 'pool': 'pitch_locations.ball.high_inside',
            'template': 'high and tight',
            'inputs': {'event_type': 'B', 'zone': 11,
                       'pitch_type_simple': 'fastball', 'batter_hand': 'R'},
        }

    def compile(self, case=None):
        return comparison.compile_case(self.case if case is None else case, 1, self.source_lines)

    def test_compiled_replay_uses_production_rng_without_selecting_by_text(self):
        fixture = self.compile()
        original = copy.deepcopy(fixture)
        self.assertEqual(set(fixture['commentaryRng']['case']), set(STREAM_NAMES))
        with patch.object(comparison, '_RecordingSelector', side_effect=AssertionError('replay must not compile')):
            self.assertEqual(comparison.replay_case(fixture, 1), 'high and tight')
        self.assertEqual(fixture, original)
        renderer = comparison._new_renderer()
        renderer._reseed_for_point(fixture, 'case', '', 'unit-test')
        for stream in STREAM_NAMES:
            self.assertIsInstance(getattr(renderer, f'rng_{stream}'), ChoiceRNG)

    def test_phrase_match_preserves_order_and_requires_contiguous_words(self):
        self.assertTrue(comparison.contains_phrase('HIGH, and tight!', 'high and tight'))
        self.assertFalse(comparison.contains_phrase('tight and high', 'high and tight'))
        self.assertFalse(comparison.contains_phrase('high but somehow still tight', 'high tight'))
        self.assertFalse(comparison.contains_phrase('high and tight', ''))
        self.assertFalse(comparison.contains_phrase('high and tight', 'hi'))

    def test_episode_identifiers_normalize_source_filenames(self):
        self.assertEqual(comparison.episode_number('episode_005.txt'), 5)
        self.assertEqual(comparison.episode_stem('005'), 'episode_005')
        for value in ('episode_005.json', '../episode_005.txt', 0, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                comparison.episode_number(value)

    def test_wrong_handedness_cannot_reach_inside_phrase(self):
        wrong = copy.deepcopy(self.case)
        wrong['inputs']['batter_hand'] = 'L'
        with self.assertRaisesRegex(ValueError, 'unreachable'):
            self.compile(wrong)

    def test_wrong_routing_fails_even_when_phrase_exists_elsewhere(self):
        wrong = copy.deepcopy(self.case)
        wrong['inputs']['event_type'] = 'C'
        with self.assertRaisesRegex(ValueError, 'unreachable'):
            self.compile(wrong)

    def test_expected_phrase_must_exist_in_source_and_replay(self):
        changed = copy.deepcopy(self.case)
        changed['expected'] = 'tight and high'
        with self.assertRaisesRegex(ValueError, 'source line'):
            self.compile(changed)
        fixture = self.compile()
        fixture['expected'] = 'ball'
        with self.assertRaisesRegex(ValueError, 'absent from replay'):
            comparison.replay_case(fixture, 1)

    def test_source_line_must_still_match_exactly(self):
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            comparison.compile_case(self.case, 1, ['The BALL is high and tight.'])
        changed = copy.deepcopy(self.case)
        changed['source_line'] = 0
        with self.assertRaisesRegex(ValueError, '1-based'):
            self.compile(changed)

    def test_compiler_searches_actual_gate_positions(self):
        case = {
            'id': 'groundout-gates', 'source_line': 1,
            'source_text': 'Roller to first.', 'expected': 'Roller to first',
            'kind': 'play_description', 'pool': 'narrative_templates.Groundout.default',
            'template': 'Roller {direction}. {fielder_name} scoops it up and fires to first {out_context_str}.',
            'inputs': {
                'outcome': 'Groundout', 'hit_data': {'location': '1B'},
                'pitch_details': {'type': 'Fastball'}, 'batter_name': 'Case Batter',
                'fielder_pos': '1B', 'fielder_name': 'Smith', 'result_outs': 1,
            },
        }
        fixture = comparison.compile_case(case, 1, [case['source_text']])
        flow = fixture['commentaryRng']['case']['flow']
        self.assertGreaterEqual(flow[0], 50)  # Skip special unassisted wording.
        self.assertLess(flow[1], 80)  # Enter the general narrative template branch.
        self.assertIn('Roller to first.', comparison.replay_case(fixture, 1))

    def test_compiler_replays_source_double_from_actual_weighted_mixed_pool(self):
        spec = json.loads((comparison.SPEC_DIR / 'episode_049.json').read_text())
        case = next(row for row in spec['cases']
                    if row['id'] == 'episode_049_double_rolls_to_wall')
        source_lines = (comparison.SOURCE_DIR / 'episode_049.txt').read_text().splitlines()
        declared_pool = comparison.get_pool(case['pool'])
        offered_pools = []
        original_choice = comparison._RecordingSelector.choice

        def observe_choices(selector, options):
            if selector.template == case['template'] and case['template'] in options:
                offered_pools.append(list(options))
            return original_choice(selector, options)

        with patch.object(comparison._RecordingSelector, 'choice', observe_choices):
            fixture = comparison.compile_case(case, 49, source_lines)
        self.assertTrue(offered_pools)
        self.assertTrue(any(any(option not in declared_pool for option in options)
                            for options in offered_pools))
        # Replay must use the persisted integers through the production RNG,
        # including the target's position within the real combined choice list.
        with patch.object(comparison, '_RecordingSelector', side_effect=AssertionError('replay must not compile')):
            rendered = comparison.replay_case(fixture, 49)
        self.assertTrue(comparison.contains_phrase(rendered, case['expected']), rendered)

    def test_mixed_pool_selector_never_injects_an_unoffered_target(self):
        selector = comparison._RecordingSelector('authored target', ['authored target'],
                                                 comparison._GatePlan(()))
        options = ['actual fallback', 'other actual fallback']
        self.assertEqual(selector.choice(options), options[0])
        self.assertFalse(selector.selected_target)
        self.assertEqual(selector.draws, [0])
        self.assertEqual(options, ['actual fallback', 'other actual fallback'])

    def test_missing_or_unconsumed_draws_are_not_silently_accepted(self):
        for draws in ([], [0, 0]):
            fixture = self.compile()
            fixture['commentaryRng']['case']['pitch'] = draws
            with self.subTest(draws=draws), self.assertRaisesRegex(ValueError, 'consumed'):
                comparison.replay_case(fixture, 1)
        fixture = self.compile()
        del fixture['commentaryRng']['case']['flow']
        with self.assertRaisesRegex(ValueError, 'all four'):
            comparison.replay_case(fixture, 1)

    def _write_catalog(self, directory):
        source_dir, spec_dir, fixture_dir = (Path(directory) / part for part in ('source', 'spec', 'fixtures'))
        source_dir.mkdir()
        spec_dir.mkdir()
        (source_dir / 'episode_001.txt').write_text(self.source_lines[0] + '\n')
        cases = []
        for index in range(3):
            case = copy.deepcopy(self.case)
            case['id'] = f'case-{index}'
            cases.append(case)
        spec = {'episode': 1, 'cases': cases}
        (spec_dir / 'episode_001.json').write_text(json.dumps(spec))
        return source_dir, spec_dir, fixture_dir, spec

    def test_complete_catalog_and_snapshot_required(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir, spec_dir, fixture_dir, _ = self._write_catalog(directory)
            counts = update_examples(source_dir, spec_dir, fixture_dir)
            self.assertEqual(counts, {1: 3})
            snapshot = fixture_dir / 'episode_001.txt'
            snapshot.write_text(snapshot.read_text().replace('high and tight', 'tight and high'))
            with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                comparison.check_catalog(source_dir, spec_dir, fixture_dir)
            snapshot.unlink()
            with self.assertRaisesRegex(ValueError, 'catalogs'):
                comparison.check_catalog(source_dir, spec_dir, fixture_dir)

    def test_source_episode_omissions_and_too_few_cases_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir, spec_dir, _, spec = self._write_catalog(directory)
            (source_dir / 'episode_005.txt').write_text('Another game.\n')
            with self.assertRaisesRegex(ValueError, 'missing=\\[5\\]'):
                comparison.load_specs(source_dir, spec_dir)
            spec['cases'].pop()
            with self.assertRaisesRegex(ValueError, 'at least three'):
                comparison.validate_spec(spec, self.source_lines)

    def test_fixture_metadata_and_expected_cannot_drift_from_spec(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir, spec_dir, fixture_dir, spec = self._write_catalog(directory)
            update_examples(source_dir, spec_dir, fixture_dir)
            fixture = json.loads((fixture_dir / 'episode_001.json').read_text())
            for field, value in (('expected', 'tight'), ('inputs', {'zone': 12})):
                changed = copy.deepcopy(fixture)
                changed['cases'][0][field] = value
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, f'{field} differs'):
                    comparison.validate_compiled_episode(changed, spec, source_dir / 'episode_001.txt')


class TestTranscriptCorpus(unittest.TestCase):
    def test_every_source_episode_has_reviewed_specs_draw_fixtures_and_snapshots(self):
        counts = check_transcript_examples()
        source_catalog = comparison.discover_episodes(comparison.SOURCE_DIR, '.txt')
        self.assertEqual(set(counts), set(source_catalog))
        self.assertTrue(all(count >= 3 for count in counts.values()))

    def test_deleting_a_whole_episode_or_reducing_coverage_cannot_pass(self):
        for counts in ({1: 4}, {1: 4, 5: 4}, {1: 4, 5: 5, 6: 3}):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                validate_transcript_counts(counts, {1: 4, 5: 5})
        validate_transcript_counts({1: 4, 5: 5}, {1: 4, 5: 5})

    def test_every_case_replay_leaves_persisted_draws_unchanged(self):
        for _, path in comparison.discover_episodes(comparison.FIXTURE_DIR).items():
            with self.subTest(episode=path.stem):
                fixture = json.loads(path.read_text())
                before = copy.deepcopy(fixture)
                first = comparison.snapshot_text(fixture)
                self.assertEqual(comparison.snapshot_text(fixture), first)
                self.assertEqual(fixture, before)


if __name__ == '__main__':
    unittest.main()
