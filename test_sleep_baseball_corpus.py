"""Honest coverage accounting and source provenance across all 21 games."""

from collections import Counter
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from commentary import GAME_CONTEXT
from sleep_baseball_corpus import (
    ROOT, corpus_paths, extract_phrases, measure_corpus, normalize_phrase,
    render_case_variants, report_corpus,
)


# (eligible inventory, supported components, supported pitch clauses).
# Counts are rounded down from the corpus scan, independently for every game.
# Pitch floors ensure easy count phrases cannot conceal lost pitch-call support.
CORPUS_FLOORS = {
    'pbp_example_1.txt': (230, 200, 75),
    'pbp_example_2.txt': (250, 220, 80),
    'pbp_example_3.txt': (200, 110, 35),
    'pbp_example_4.txt': (280, 245, 80),
    'episode_001.txt': (360, 175, 40),
    'episode_005.txt': (270, 125, 45),
    'episode_011.txt': (280, 190, 65),
    'episode_013.txt': (420, 285, 120),
    'episode_020.txt': (300, 250, 95),
    'episode_029.txt': (310, 255, 90),
    'episode_035.txt': (280, 230, 75),
    'episode_037.txt': (300, 265, 90),
    'episode_039.txt': (310, 230, 80),
    'episode_041.txt': (270, 230, 80),
    'episode_045.txt': (310, 235, 80),
    'episode_046.txt': (340, 260, 85),
    'episode_049.txt': (300, 240, 85),
    'episode_050.txt': (200, 165, 60),
    'episode_051.txt': (200, 155, 45),
    'episode_052.txt': (270, 220, 70),
    'episode_053.txt': (250, 215, 75),
}


class TestSleepBaseballCorpus(unittest.TestCase):
    def test_all_four_examples_and_seventeen_episodes_are_inventoried(self):
        paths = corpus_paths()
        self.assertEqual(len(paths), 21)
        self.assertEqual(sum(path.name.startswith('pbp_example_') for path in paths), 4)
        self.assertEqual(sum(path.name.startswith('episode_') for path in paths), 17)
        reports = measure_corpus()
        self.assertEqual([r.source_file for r in reports], [p.relative_to(ROOT).as_posix() for p in paths])
        self.assertEqual({Path(r.source_file).name for r in reports}, set(CORPUS_FLOORS))
        for report in reports:
            with self.subTest(source=report.source_file):
                eligible_min, supported_min, pitch_min = CORPUS_FLOORS[Path(report.source_file).name]
                self.assertGreaterEqual(report.eligible, eligible_min, 'Extractor lost eligible source clauses.')
                self.assertGreaterEqual(report.supported, supported_min, 'Renderer lost component phrase support.')
                self.assertGreaterEqual(report.kinds['pitch']['supported'], pitch_min, 'Renderer lost pitch-call support.')
                self.assertGreater(report.eligible, 0)
                self.assertLessEqual(report.supported, report.eligible)
                self.assertEqual(len(report.uncovered), report.eligible - report.supported)
                self.assertEqual(sum(c['eligible'] for c in report.kinds.values()), report.eligible)

    def test_every_automatic_candidate_retains_exact_source_provenance(self):
        for path in corpus_paths():
            text = path.read_text()
            lines = text.splitlines()
            previous_line = 0
            for candidate in extract_phrases(text, path.relative_to(ROOT).as_posix()):
                with self.subTest(source=path.name, line=candidate.source_line):
                    self.assertGreaterEqual(candidate.source_line, previous_line)
                    self.assertIn(candidate.source_phrase, lines[candidate.source_line - 1])
                    self.assertTrue(candidate.source_phrase.strip())
                    previous_line = candidate.source_line

    def test_commentary_and_batted_ball_locations_are_not_pitch_calls(self):
        text = ('It is a perfect night for a ball game.\n'
                'The pitch... A low line drive drops for a base hit.\n'
                '[TTS SPLIT HERE DELAY:8.5s]')
        self.assertEqual(extract_phrases(text, 'source.txt'), [])

    def test_pitch_and_resulting_count_are_separate_ordered_clauses(self):
        candidates = extract_phrases(
            'The one-two pitch... Slider misses low, two and two.', 'source.txt')
        self.assertEqual([c.source_phrase for c in candidates], ['Slider misses low', 'two and two'])
        self.assertEqual([c.kind for c in candidates], ['pitch', 'count'])
        self.assertEqual(candidates[0].input['code'], 'B')
        self.assertEqual((candidates[0].input['balls'], candidates[0].input['strikes']), (1, 2))
        self.assertEqual((candidates[1].input['balls'], candidates[1].input['strikes']), (2, 2))

    def test_cut_on_it_and_missed_is_a_swinging_strike(self):
        for phrase in ('Fastball, cut on it and missed', 'Fastball, cut on it, missed'):
            candidates = extract_phrases(f'The pitch... {phrase}. Oh and one.', 'source.txt')
            self.assertEqual(candidates[0].input['code'], 'S')
            self.assertEqual(candidates[0].source_phrase, phrase)

    def test_explicit_first_foul_cannot_support_another_foul(self):
        phrase = normalize_phrase('he fouls another one off')
        first = {'kind': 'foul', 'input': {'consecutive_fouls': 0}}
        repeated = {'kind': 'foul', 'input': {'consecutive_fouls': 1}}
        unknown = {'kind': 'foul', 'input': {}}
        self.assertNotIn(phrase, {normalize_phrase(v) for v in render_case_variants(first)})
        self.assertIn(phrase, {normalize_phrase(v) for v in render_case_variants(repeated)})
        self.assertIn(phrase, {normalize_phrase(v) for v in render_case_variants(unknown)})

    def test_terminal_or_invalid_counts_are_not_supported_count_calls(self):
        for balls, strikes in ((3, 3), (4, 2), (-1, 0), (0, -1)):
            self.assertEqual(render_case_variants(
                {'kind': 'count', 'input': {'code': 'S', 'balls': balls, 'strikes': strikes}}), set())
        self.assertFalse(any(c.kind == 'count' for c in extract_phrases(
            'Fastball misses low, three and three.', 'source.txt')))

    def test_capitalized_count_cues_are_retained_as_source_clauses(self):
        phrases = extract_phrases('Slider misses low. It\'s two and one.', 'source.txt')
        self.assertEqual(phrases[-1].kind, 'count')
        self.assertEqual(phrases[-1].source_phrase, "It's two and one")

    def test_compound_pitcher_name_comes_from_source_not_an_invented_first_name(self):
        text = ('Starting pitcher, Javier Von Neumann.\n'
                'The one-one pitch... Slider misses low, and Von Neumann falls behind two and one.')
        counts = [c for c in extract_phrases(text, 'source.txt') if c.kind == 'count']
        self.assertEqual(counts[0].input['pitcher_name'], 'Javier Von Neumann')
        self.assertEqual(counts[0].input['pitcher_name_source_line'], 1)
        unsupported = extract_phrases('The pitch... and Von Neumann falls behind three and one.', 'source.txt')
        self.assertEqual(unsupported[-1].input['pitcher_name'], 'Von Neumann')
        self.assertNotIn('pitcher_name_source_line', unsupported[-1].input)

    def test_normalization_preserves_word_order_repetition_and_asr_words(self):
        self.assertEqual(normalize_phrase('Curveball, called a strike.'), normalize_phrase('curveball called a strike'))
        for altered in ('Curveball called strike', 'Called a strike curveball',
                        'Curveball called a a strike', 'Curveball cold a strike'):
            self.assertNotEqual(normalize_phrase('Curveball called a strike'), normalize_phrase(altered))
        self.assertNotEqual(normalize_phrase('two and two'), normalize_phrase('2 and 2'))

    def test_unused_template_pool_is_not_proof_of_renderer_support(self):
        # Main Street appears in the location default pool, but called strikes
        # at the center zone actually route through strike_called_one.
        self.assertIn('right down Main Street', GAME_CONTEXT['pitch_locations']['strike']['default'])
        case = {'kind': 'pitch', 'input': {'code': 'C', 'zone': 5, 'balls': 0,
                                         'strikes': 0, 'pitch_type': 'Fastball', 'batter_hand': 'R'}}
        variants = {normalize_phrase(v) for v in render_case_variants(case)}
        self.assertNotIn(normalize_phrase('Fastball, right down Main Street'), variants)
        # A new reachable choice is discovered dynamically from actual output.
        pool = GAME_CONTEXT['narrative_strings']['strike_called_one']
        with patch.dict(GAME_CONTEXT['narrative_strings'], strike_called_one=pool + ['right down Main Street']):
            variants = {normalize_phrase(v) for v in render_case_variants(case)}
            self.assertIn(normalize_phrase('Fastball, right down Main Street'), variants)

    def test_explicit_zone_cannot_support_a_contradictory_swing_location(self):
        case = {'kind': 'pitch', 'input': {'code': 'S', 'zone': 8, 'balls': 0,
                                         'strikes': 0, 'pitch_type': 'Slider', 'batter_hand': 'R'}}
        variants = {normalize_phrase(v) for v in render_case_variants(case)}
        self.assertNotIn(normalize_phrase('Swing and a miss on a high slider'), variants)

    def test_curated_cases_cover_every_source_and_emit_expected_phrases(self):
        manifest = json.loads((ROOT / 'sleep_baseball_phrase_cases.json').read_text())
        cases = manifest['cases']
        self.assertEqual(manifest['schema_version'], 1)
        expected_sources = {p.relative_to(ROOT).as_posix() for p in corpus_paths()}
        self.assertEqual(set(c['source_file'] for c in cases), expected_sources)
        self.assertTrue(all(count >= 3 for count in Counter(c['source_file'] for c in cases).values()))
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case['id']):
                line = (ROOT / case['source_file']).read_text().splitlines()[case['source_line'] - 1]
                self.assertIn(case['source_phrase'], line)
                self.assertEqual(normalize_phrase(case['source_phrase']), normalize_phrase(case['expected_phrase']))
                actual = {normalize_phrase(v) for v in render_case_variants(case)}
                self.assertIn(normalize_phrase(case['expected_phrase']), actual)

    def test_report_states_component_scope_and_lists_all_sources_and_uncovered_rows(self):
        output = io.StringIO()
        reports = report_corpus(uncovered_limit=1, output=output)
        text = output.getvalue()
        self.assertIn('not full-game', text)
        self.assertIn('numeric spelling remain significant', text)
        for report in reports:
            self.assertIn(report.source_file, text)
            self.assertIn(f'{report.supported}/{report.eligible}', text)
            if report.uncovered:
                first = report.uncovered[0]
                self.assertIn(f"{first['source_file']}:{first['source_line']}", text)


if __name__ == '__main__':
    unittest.main()
