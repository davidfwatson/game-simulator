"""Regression checks for phrase coverage measurements."""

import unittest

from pbp_alignment import alignment_metrics, content_text, positional_line_match


class TestPbpAlignment(unittest.TestCase):
    def test_tts_markers_cannot_improve_content_coverage(self):
        target = 'The fastball misses low and inside.\nA runner takes second.'
        rendered = 'The curveball catches the outside corner.\nA runner stays first.'
        marker = '[TTS SPLIT HERE DELAY:8.5s]'
        with_markers = alignment_metrics(
            f'{marker}\n{target}\n{marker}', f'{marker}\n{rendered}\n{marker}'
        )
        self.assertEqual(with_markers, alignment_metrics(target, rendered))
        self.assertEqual(with_markers.target_lines, 2)
        self.assertEqual(with_markers.exact, 0)

    def test_tts_boundaries_do_not_break_content_phrases(self):
        target = 'And the fastball\nmisses low and inside.'
        rendered = 'And the fastball\n[TTS SPLIT HERE DELAY:9.5s]\nmisses low and inside.'
        metrics = alignment_metrics(target, rendered)
        self.assertEqual(metrics.word_jaccard, 1.0)
        self.assertEqual(metrics.ngram_coverage, 1.0)
        self.assertEqual(metrics.exact, 2)

    def test_all_line_metrics_retain_playback_markers(self):
        marker = '[TTS SPLIT HERE DELAY:8.5s]'
        target = f'{marker}\nThe fastball misses low.'
        rendered = f'{marker}\nA curveball crosses home.'
        all_lines = alignment_metrics(target, rendered, content_only=False)
        self.assertEqual(all_lines.target_lines, 2)
        self.assertEqual(all_lines.exact, 1)
        self.assertGreater(all_lines.word_jaccard, alignment_metrics(target, rendered).word_jaccard)

    def test_exact_lines_require_word_order_and_repetition(self):
        target = 'One runner on first and two runners on second.'
        variants = (
            'Two runners on first and one runner on second.',
            'One runner on first and two runners on second second.',
        )
        for rendered in variants:
            with self.subTest(rendered=rendered):
                exact, near90, near75, count = positional_line_match(target, rendered)
                self.assertEqual((exact, near90, near75, count), (0, 1, 0, 1))

    def test_normalized_count_phrases_still_match_exactly(self):
        target = 'Curveball called a strike. Oh and one.'
        rendered = 'curveball called strike, oh-one.'
        self.assertEqual(positional_line_match(target, rendered), (1, 0, 0, 1))

    def test_five_grams_measure_source_phrase_recall(self):
        target = 'And the pitch is on the way'
        rendered = f'{target} while the runner takes a lead'
        metrics = alignment_metrics(target, rendered)
        self.assertEqual(metrics.ngram_coverage, 1.0)
        self.assertLess(metrics.word_jaccard, 1.0)

    def test_each_rendered_line_matches_at_most_once(self):
        target = 'The pitch is on the way.\nThe pitch is on the way.'
        metrics = alignment_metrics(target, 'The pitch is on the way.')
        self.assertEqual(metrics.exact, 1)
        self.assertEqual(metrics.exact_fraction, 0.5)

    def test_empty_or_marker_only_text_has_zero_coverage(self):
        metrics = alignment_metrics('[TTS SPLIT HERE DELAY:8.5s]', '')
        self.assertEqual(metrics.word_jaccard, 0.0)
        self.assertEqual(metrics.ngram_coverage, 0.0)
        self.assertEqual(metrics.exact_fraction, 0.0)
        self.assertEqual(content_text(''), '')


if __name__ == '__main__':
    unittest.main()
