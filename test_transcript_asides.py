"""Host-aside annotations: validation, catalog consistency, and metric exclusion."""

import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import full_transcript_comparison
from pbp_comparison import PBPExample, compare_example, compare_transcripts
from sleep_baseball_corpus import corpus_paths, measure_corpus
import transcript_asides
from transcript_asides import (
    ASIDE_DIR, CATEGORIES, ROOT, load_asides, metric_source_text, parse_asides, strip_asides,
)
from transcript_game_fixtures import LEDGER_DIR

SOURCE = ('And the pitch... Fastball, called strike one.\n'
          'The two-oh pitch... Two and oh. And the crew chief is calling time, there is a goat in center field. '
          "There's the two-oh pitch.\n"
          'Producer Phil has passed me a note.\n'
          'He says the goat belongs to the mayor.\n'
          'Ball four.\n')


def annotation(asides, text=SOURCE, name='source.txt'):
    return {'source_file': name, 'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'asides': asides}


GOAT = {'line': 2, 'text': 'And the crew chief is calling time, there is a goat in center field.',
        'category': 'story'}
NOTE = {'line': 3, 'end_line': 4, 'category': 'banter'}


class TestAsideValidation(unittest.TestCase):
    def test_substring_and_whole_line_spans_are_located_exactly(self):
        spans = parse_asides(annotation([GOAT, NOTE]), SOURCE, 'source.txt')
        line = SOURCE.splitlines()[1]
        self.assertEqual(line[spans[0].start:spans[0].end], GOAT['text'])
        self.assertEqual([(s.line, s.start, s.category) for s in spans[1:]],
                         [(3, 0, 'banter'), (4, 0, 'banter')])

    def test_changed_source_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            parse_asides(annotation([GOAT]), SOURCE.replace('goat', 'moose'), 'source.txt')

    def test_wrong_source_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'annotation names'):
            parse_asides(annotation([GOAT]), SOURCE, 'other.txt')

    def test_substring_must_match_its_line_exactly(self):
        for entry in (dict(GOAT, line=1), dict(GOAT, text=GOAT['text'].lower()),
                      dict(GOAT, text=GOAT['text'].replace('.', '…'))):
            with self.subTest(entry=entry), self.assertRaisesRegex(ValueError, 'exact substring'):
                parse_asides(annotation([entry]), SOURCE, 'source.txt')

    def test_repeated_substring_needs_an_occurrence(self):
        entry = {'line': 2, 'text': 'two-oh pitch', 'category': 'banter'}
        with self.assertRaisesRegex(ValueError, 'occurs 2 times'):
            parse_asides(annotation([entry]), SOURCE, 'source.txt')
        span, = parse_asides(annotation([dict(entry, occurrence=2)]), SOURCE, 'source.txt')
        self.assertEqual(span.start, SOURCE.splitlines()[1].rindex('two-oh pitch'))
        with self.assertRaisesRegex(ValueError, 'out of range'):
            parse_asides(annotation([dict(entry, occurrence=3)]), SOURCE, 'source.txt')

    def test_malformed_entries_are_rejected(self):
        cases = {
            'category': dict(GOAT, category='colour'),
            'outside the source': dict(NOTE, end_line=9),
            'within one line': dict(GOAT, end_line=3),
            'unknown fields': dict(GOAT, start=4),
            'must contain words': dict(GOAT, text='...'),
            'occurrence requires text': dict(NOTE, occurrence=1),
        }
        for message, entry in cases.items():
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                parse_asides(annotation([entry]), SOURCE, 'source.txt')

    def test_whole_line_aside_cannot_cover_a_blank_line(self):
        text = 'Ball one.\n\nBall two.\n'
        with self.assertRaisesRegex(ValueError, 'blank line 2'):
            parse_asides(annotation([{'line': 1, 'end_line': 3, 'category': 'banter'}], text), text, 'source.txt')

    def test_overlapping_asides_are_rejected(self):
        inner = {'line': 2, 'text': 'there is a goat', 'category': 'story'}
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            parse_asides(annotation([GOAT, inner]), SOURCE, 'source.txt')

    def test_strip_preserves_line_numbers_and_empties_whole_line_asides(self):
        stripped = strip_asides(SOURCE, parse_asides(annotation([GOAT, NOTE]), SOURCE, 'source.txt'))
        lines = stripped.splitlines()
        self.assertEqual(len(lines), len(SOURCE.splitlines()))
        self.assertEqual(lines[1], "The two-oh pitch... Two and oh. There's the two-oh pitch.")
        self.assertEqual(lines[2:4], ['', ''])
        self.assertEqual(lines[4], 'Ball four.')
        self.assertTrue(stripped.endswith('\n'))


class TestAsideCatalog(unittest.TestCase):
    def test_every_source_has_a_valid_annotation_file(self):
        sources = {path.stem: path for path in corpus_paths()}
        self.assertEqual(len(sources), 21)
        self.assertEqual({path.stem for path in ASIDE_DIR.glob('*.json')}, set(sources))
        for stem, path in sources.items():
            with self.subTest(source=stem):
                data = json.loads((ASIDE_DIR / f'{stem}.json').read_text(encoding='utf-8'))
                self.assertEqual(data['source_file'], path.relative_to(ROOT).as_posix())
                for entry in data['asides']:
                    self.assertIn(entry['category'], CATEGORIES)
                    self.assertTrue(entry.get('note', '').strip(), 'Describe each aside for later reuse.')
                load_asides(path)

    def test_episode_asides_are_marked_but_never_dominate_a_source(self):
        for row in transcript_asides.summarize():
            with self.subTest(source=row['source_file']):
                self.assertGreater(row['aside_spans'], 0)
                self.assertLess(row['aside_words'], 0.35 * row['source_words'])

    def test_asides_never_remove_a_recorded_pitch_or_appearance(self):
        for ledger_path in sorted(LEDGER_DIR.glob('episode_*.json')):
            ledger = json.loads(ledger_path.read_text())
            source = ROOT / 'transcripts' / 'sleep_baseball' / ledger['source_file']
            lines = metric_source_text(source).splitlines()
            for index, play in enumerate(ledger['plays']):
                with self.subTest(episode=ledger['episode'], play=index):
                    reference = ' '.join(lines[play['source_start'] - 1:play['source_end']])
                    self.assertRegex(reference, r'\w')
                    for pitch in play.get('pitches', []):
                        self.assertRegex(lines[pitch['line'] - 1], r'\w',
                                         f"line {pitch['line']} holds a recorded pitch")

    def test_phrases_the_renderer_is_tested_to_produce_are_never_asides(self):
        stripped = {path.name: metric_source_text(path).splitlines() for path in corpus_paths()}
        words = lambda text: re.findall(r'\w+', text.casefold())
        for spec in sorted((ROOT / 'transcript_cases').glob('episode_*.json')):
            data = json.loads(spec.read_text())
            for case in data['cases']:
                with self.subTest(case=case['id']):
                    line = ' '.join(words(stripped[data['episode']][case['source_line'] - 1]))
                    self.assertIn(' '.join(words(case['expected'])), line)
        phrase_cases = json.loads((ROOT / 'sleep_baseball_phrase_cases.json').read_text())['cases']
        for case in phrase_cases:
            with self.subTest(case=case['id']):
                line = stripped[Path(case['source_file']).name][case['source_line'] - 1]
                self.assertIn(' '.join(words(case['source_phrase'])), ' '.join(words(line)))


class TestMetricsIgnoreAsides(unittest.TestCase):
    RENDERED = 'And the pitch... Fastball, called strike one.\nBall four.\n'

    def write_root(self, root, text, asides):
        (root / 'pbp_example_9.txt').write_text(text)
        (root / 'transcript_asides').mkdir()
        (root / 'transcript_asides' / 'pbp_example_9.json').write_text(
            json.dumps(annotation(asides, text, 'pbp_example_9.txt')))

    def test_pbp_example_metrics_score_as_if_the_aside_were_cut(self):
        example = PBPExample(9, target_skip=0, rendered_skip=0)
        aside_line = 'Producer Phil reminds me the goat belongs to the mayor.'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_root(root, f'And the pitch... Fastball, called strike one.\n{aside_line}\nBall four.\n',
                            [{'line': 2, 'category': 'banter'}])
            marked = compare_example(example, self.RENDERED, root)
        cut = compare_transcripts('And the pitch... Fastball, called strike one.\n\nBall four.\n', self.RENDERED)
        self.assertEqual(marked, cut)
        self.assertEqual(marked.content_lines.total, 2)
        unmarked = compare_transcripts(f'And the pitch... Fastball, called strike one.\n{aside_line}\nBall four.\n',
                                       self.RENDERED)
        self.assertLess(unmarked.jaccard, marked.jaccard)
        self.assertEqual(unmarked.content_lines.total, 3)

    def test_component_coverage_skips_clauses_inside_an_aside(self):
        text = ('The one-two pitch... Slider misses low, two and two.\n'
                'Phil says the slider misses low, two and two, every time he pitches in his backyard.\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_root(root, text, [])
            unmarked, = measure_corpus(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_root(root, text, [{'line': 2, 'category': 'banter'}])
            marked, = measure_corpus(root)
        self.assertGreater(unmarked.eligible, marked.eligible)
        self.assertTrue(all(row['source_line'] == 1 for row in marked.uncovered))
        self.assertEqual(marked.eligible, 2)

    def test_full_broadcast_metrics_ignore_an_injected_marked_aside(self):
        source = (ROOT / 'transcripts' / 'sleep_baseball' / 'episode_049.txt').read_text()
        ledger = json.loads((LEDGER_DIR / 'episode_049.json').read_text())
        line_number = ledger['plays'][3]['pitches'][0]['line']
        aside = 'And producer Phil tells me a skydiver has landed in the parking lot.'
        lines = source.splitlines()
        lines[line_number - 1] += ' ' + aside
        injected = '\n'.join(lines) + '\n'
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'src').mkdir()
            (tmp / 'asides').mkdir()
            (tmp / 'src' / 'episode_049.txt').write_text(source)
            with patch.object(full_transcript_comparison, 'SOURCE_DIR', tmp / 'src'), \
                 patch.object(transcript_asides, 'ASIDE_DIR', tmp / 'asides'):
                baseline = full_transcript_comparison.compare_game(49)
                (tmp / 'src' / 'episode_049.txt').write_text(injected)
                unmarked = full_transcript_comparison.compare_game(49)
                (tmp / 'asides' / 'episode_049.json').write_text(json.dumps(annotation(
                    [{'line': line_number, 'text': aside, 'category': 'story'}], injected,
                    'episode_049.txt')))
                marked = full_transcript_comparison.compare_game(49)
        keys = ('jaccard', 'ngram', 'content_exact', 'mean_play_word_coverage')
        self.assertEqual({k: marked[k] for k in keys}, {k: baseline[k] for k in keys})
        self.assertLess(unmarked['plays'][3]['ordered_word_coverage'],
                        baseline['plays'][3]['ordered_word_coverage'])


if __name__ == '__main__':
    unittest.main()
