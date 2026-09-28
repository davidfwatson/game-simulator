"""Regression coverage for explicit commentary authoring and faithful tracing."""

import copy
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import fixture_utils
import pbp_tools
from renderers.narrative.renderer import NarrativeRenderer
from renderers.randomness import ChoiceRNG


class TestPbpTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name('test_fixture_pbp_example_1.json')
        cls.fixture = json.loads(path.read_text())

    def setUp(self):
        self.data = copy.deepcopy(self.fixture)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / 'fixture.json'
        self.path.write_text(json.dumps(self.data))

    def trace(self, data=None):
        tracer = pbp_tools.TracingRenderer(self.data if data is None else data)
        rendered = tracer.render()
        return tracer, rendered

    def entry(self, key, data=None):
        tracer, _ = self.trace(data)
        return next(entry for entry in tracer.seed_log if entry['key'] == key)

    def test_tracing_preserves_rendered_output_and_includes_init(self):
        expected = NarrativeRenderer(self.data).render()
        tracer, actual = self.trace()
        self.assertEqual(expected, actual)
        self.assertEqual(tracer.seed_log[0]['key'], 'init')
        self.assertGreater(len(tracer.seed_log[0]['rngs']['color'].calls), 2)
        self.assertEqual(len({entry['key'] for entry in tracer.seed_log}), len(tracer.seed_log))

    def test_repeated_trace_resets_logs_and_render_state(self):
        tracer, first = self.trace()
        keys = [entry['key'] for entry in tracer.seed_log]
        self.assertEqual(tracer.render(), first)
        self.assertEqual([entry['key'] for entry in tracer.seed_log], keys)
        self.assertEqual(keys.count('init'), 1)

    def test_tracing_preserves_fallback_random_values(self):
        def clear_metadata(value):
            if isinstance(value, dict):
                value.pop('commentaryRng', None)
                for child in value.values():
                    clear_metadata(child)
            elif isinstance(value, list):
                for child in value:
                    clear_metadata(child)
        clear_metadata(self.data)
        _, actual = self.trace()
        self.assertEqual(NarrativeRenderer(self.data).render(), actual)
        wrapped = pbp_tools.TracingRNG(random.Random(72))
        plain = random.Random(72)
        for _ in range(10):
            self.assertEqual(wrapped.choice(['same', 'same', 'other']), plain.choice(['same', 'same', 'other']))
            self.assertEqual(wrapped.random(), plain.random())

    def test_large_choice_pool_and_duplicate_values_keep_selected_index(self):
        wrapped = pbp_tools.TracingRNG(ChoiceRNG([257, 2], 1), 'play')
        self.assertEqual(wrapped.choice(range(300)), 257)
        self.assertEqual(wrapped.calls[0]['draw'], 257)
        self.assertEqual(wrapped.choice(['same'] * 3), 'same')
        self.assertEqual(wrapped.calls[1]['selected_index'], 2)

    def test_random_draw_float_precision(self):
        wrapped = pbp_tools.TracingRNG(ChoiceRNG([29, 57, 99], 1))
        for value in (29, 57, 99):
            self.assertEqual(wrapped.random(), value / 100)
            self.assertEqual(wrapped.calls[-1]['draw'], value)

    def test_duplicate_timestamps_target_correct_event(self):
        play = self.data['liveData']['plays']['allPlays'][0]
        first, second = play['playEvents'][:2]
        second['startTime'] = first['startTime']
        first_before = copy.deepcopy(first)
        entry = self.entry('play:0:event:1')
        call = entry['rngs']['pitch'].calls[0]
        desired = (call['selected_index'] + 1) % call['pool_size']
        pbp_tools.edit_commentary_draws(self.data, 0, 'event_1', {('pitch', 0): desired})
        self.assertEqual(first, first_before)
        self.assertEqual(second['startTime'], first['startTime'])
        updated = self.entry('play:0:event:1')
        self.assertEqual(updated['rngs']['pitch'].calls[0]['selected_index'], desired)

    def test_edit_late_init_choice_preserves_all_other_observed_draws(self):
        original = self.entry('init')
        calls = original['rngs']['color'].calls
        index = next(i for i, call in enumerate(calls) if i > 2 and call['type'] == 'choice' and call['pool_size'] > 1)
        desired = (calls[index]['selected_index'] + 1) % calls[index]['pool_size']
        timestamp = self.data['gameData']['datetime']['dateTime']
        _, _, draws = pbp_tools.edit_commentary_draws(self.data, None, 'init', {('color', index): desired})
        self.assertEqual(draws['color'][index], desired)
        for stream, rng in original['rngs'].items():
            for i, call in enumerate(rng.calls):
                if (stream, i) != ('color', index):
                    self.assertEqual(draws[stream][i], call['draw'])
        self.assertEqual(self.data['gameData']['datetime']['dateTime'], timestamp)
        self.assertEqual(self.entry('init')['rngs']['color'].calls[index]['selected_index'], desired)

    def test_unused_explicit_draws_survive_materialization(self):
        original = self.entry('play:0:event:0')
        count = len(original['rngs']['pitch'].calls)
        owner = original['owner']
        owner['commentaryRng']['event']['pitch'] = [call['draw'] for call in original['rngs']['pitch'].calls] + [198, 284]
        updated = self.entry('play:0:event:0')
        draws = pbp_tools.materialize_trace_entry(updated)
        self.assertEqual(draws['pitch'][count:], [198, 284])

    def test_materializing_fallback_point_preserves_output(self):
        event = self.data['liveData']['plays']['allPlays'][0]['playEvents'][0]
        event.pop('commentaryRng', None)
        tracer, original = self.trace()
        entry = next(entry for entry in tracer.seed_log if entry['key'] == 'play:0:event:0')
        pbp_tools.materialize_trace_entry(entry)
        self.assertEqual(NarrativeRenderer(self.data).render(), original)

    def test_invalid_edits_rejected_without_mutation(self):
        original = copy.deepcopy(self.data)
        for overrides in ({('bad', 0): 1}, {('pitch', -1): 0},
                          {('pitch', 999): 0}, {('pitch', 0): -1},
                          {('pitch', 0): 100000}, {('pitch', 0): True}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                pbp_tools.edit_commentary_draws(self.data, 0, 'event_0', overrides)
        self.assertEqual(self.data, original)
        for play_index in (-1, len(self.data['liveData']['plays']['allPlays']), None):
            with self.subTest(play_index=play_index), self.assertRaises(ValueError):
                pbp_tools.get_rng_point(self.data, play_index, 'play_start')

    def test_set_gate_can_edit_late_call_and_preserves_timestamp(self):
        args = SimpleNamespace(json_file=self.path, play=0, point='play_start', stream='color',
                               call=2, below=None, above=.8, dry_run=False)
        with redirect_stdout(io.StringIO()):
            pbp_tools.cmd_set_gate(args)
        changed = json.loads(self.path.read_text())
        updated = self.entry('play:0:start', changed)
        self.assertGreaterEqual(updated['rngs']['color'].calls[2]['result'], .8)
        self.assertEqual(changed['liveData']['plays']['allPlays'][0]['about'], self.data['liveData']['plays']['allPlays'][0]['about'])

    def test_gate_rejects_choice_calls_and_impossible_thresholds(self):
        args = SimpleNamespace(json_file=self.path, play=0, point='event_0', stream='pitch',
                               call=0, below=.2, above=None, dry_run=False)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'expected random'):
            pbp_tools.cmd_set_gate(args)
        for below, above in ((0, None), (None, 1), (float('nan'), None), (None, 1.1)):
            args.below, args.above = below, above
            with self.subTest(below=below, above=above), self.assertRaises(ValueError):
                pbp_tools.cmd_set_gate(args)
        self.assertEqual(self.path.read_bytes(), before)

    def test_choice_and_gate_dry_runs_never_write(self):
        before = self.path.read_bytes()
        choice = SimpleNamespace(json_file=self.path, play=None, point='init', set=['color:0:0'], dry_run=True)
        gate = SimpleNamespace(json_file=self.path, play=0, point='play_start', stream='color',
                               call=2, below=.2, above=None, dry_run=True)
        for command, args in ((pbp_tools.cmd_set_choice, choice), (pbp_tools.cmd_set_gate, gate)):
            output = io.StringIO()
            with redirect_stdout(output):
                command(args)
            self.assertIn('[DRY RUN]', output.getvalue())
            self.assertEqual(self.path.read_bytes(), before)

    def test_trace_play_filter_uses_structural_keys(self):
        args = SimpleNamespace(json_file=self.path, play=0, verbose=True, output=None)
        output = io.StringIO()
        with redirect_stdout(output):
            pbp_tools.cmd_trace(args)
        self.assertIn('POINT: play:0:event:0', output.getvalue())
        self.assertNotIn('POINT: play:1:', output.getvalue())
        self.assertNotIn('POINT: init', output.getvalue())

    def test_fixture_draw_setter_supports_any_file_and_any_length(self):
        other_stream = copy.deepcopy(self.data['liveData']['plays']['allPlays'][0]['playEvents'][0]['commentaryRng']['event']['flow'])
        with redirect_stdout(io.StringIO()):
            fixture_utils.set_draws(0, 'event_0', fixture=self.path, pitch=[300, 201, 99, 0, 8])
        changed = json.loads(self.path.read_text())
        event = changed['liveData']['plays']['allPlays'][0]['playEvents'][0]
        self.assertEqual(event['commentaryRng']['event']['pitch'], [300, 201, 99, 0, 8])
        self.assertEqual(event['commentaryRng']['event']['flow'], other_stream)
        self.assertEqual(event['startTime'], self.data['liveData']['plays']['allPlays'][0]['playEvents'][0]['startTime'])
        before = self.path.read_bytes()
        for streams in ({'pitch': [True]}, {'pitch': [-1]}, {'pitch': 123}, {'unknown': [1]}):
            with self.subTest(streams=streams), self.assertRaises(ValueError):
                fixture_utils.set_draws(0, 'event_0', fixture=self.path, **streams)
        self.assertEqual(self.path.read_bytes(), before)

    def test_cli_rejects_invalid_draw_with_nonzero_exit(self):
        before = self.path.read_bytes()
        argv = ['pbp_tools.py', 'set-choice', str(self.path), '--play', '0', '--point', 'event_0', '--set', 'pitch:-1:0']
        with patch('sys.argv', argv), patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit) as error:
            pbp_tools.main()
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_search_discovers_new_nested_pools(self):
        context = {
            'new_phrases': {'nested': ['New turn of phrase']},
            'narrative_templates': {
                'Single': {'bloop': ['A phrase for a single']},
                'Double': {'wall': ['A phrase for a double']},
            },
        }
        with patch.object(pbp_tools, 'GAME_CONTEXT', context):
            results = pbp_tools.search_all_pools('PHRASE', outcome='Single')
        self.assertEqual([item['pool'] for item in results],
                         ['new_phrases.nested', 'narrative_templates.Single.bloop'])

    def test_diff_handles_empty_transcript(self):
        target = Path(self.tempdir.name) / 'empty.txt'
        target.write_text('')
        args = SimpleNamespace(json_file=self.path, target_file=target,
                               verbose=False, all=False, output=None)
        output = io.StringIO()
        with redirect_stdout(output):
            pbp_tools.cmd_diff(args)
        self.assertIn('Content lines in target: 0', output.getvalue())


if __name__ == '__main__':
    unittest.main()
