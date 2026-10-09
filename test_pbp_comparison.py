"""Regression coverage for transcript scoring and new-example discovery."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pbp_comparison import (
    LineMatch,
    PBPExample,
    compare_transcripts,
    discover_pbp_examples,
    normalize_line,
    positional_line_match,
    positional_line_match_content,
)


class TestTranscriptComparison(unittest.TestCase):
    def test_count_and_punctuation_variants_are_equivalent(self):
        self.assertEqual(
            normalize_line("Called a strike. Oh and two."),
            normalize_line("called strike, oh-two."),
        )

    def test_word_order_and_repetition_are_not_exact_matches(self):
        for rendered in ("throws Cole to Smith", "Cole throws throws to Smith"):
            with self.subTest(rendered=rendered):
                self.assertEqual(
                    positional_line_match("Cole throws to Smith", rendered),
                    LineMatch(0, 1, 0, 1),
                )

    def test_rendered_line_cannot_be_reused(self):
        self.assertEqual(positional_line_match("Ball one.\nBall one.", "Ball one."), LineMatch(1, 0, 0, 2))

    def test_exact_match_takes_priority_over_word_overlap(self):
        self.assertEqual(
            positional_line_match("Cole throws to Smith", "Smith throws to Cole\nCole throws to Smith"),
            LineMatch(1, 0, 0, 1),
        )

    def test_positional_window_prevents_distant_match(self):
        self.assertEqual(
            positional_line_match("Ball one.\nCalled strike.", "Called strike.\nBall one.",
                                  wiggle_pct=0, wiggle_min=0),
            LineMatch(0, 0, 0, 2),
        )

    def test_content_score_does_not_count_tts_markers(self):
        target = "[TTS SPLIT 1s]\nCole hits a single.\n[TTS SPLIT 1s]"
        rendered = "[TTS SPLIT 1s]\nSmith strikes out.\n[TTS SPLIT 1s]"
        self.assertEqual(positional_line_match(target, rendered), LineMatch(2, 0, 0, 3))
        self.assertEqual(positional_line_match_content(target, rendered), LineMatch(0, 0, 0, 1))
        self.assertTrue(compare_transcripts(target, rendered).failures(
            PBPExample(1, 0, jaccard_min=0, ngram_min=0, line_exact_min=0, content_exact_min=0.1)
        ))

    def test_empty_input_cannot_satisfy_comparison_minimums(self):
        scores = compare_transcripts("\n", "")
        self.assertEqual(scores.all_lines, LineMatch(0, 0, 0, 0))
        self.assertEqual(scores.jaccard, 0)
        self.assertEqual(scores.ngram, 0)
        self.assertEqual(len(scores.failures(PBPExample(1, 0))), 3)


class TestPBPDiscovery(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.example = PBPExample(5, target_skip=12)
        self.catalog = (self.example,)
        for name in (self.example.target_file, self.example.fixture_file, self.example.snapshot_file):
            (self.root / name).touch()

    def test_registered_example_is_discovered(self):
        self.assertEqual(discover_pbp_examples(self.root, self.catalog), self.catalog)

    def test_new_reference_cannot_be_silently_omitted(self):
        (self.root / "pbp_example_6.txt").touch()
        with self.assertRaisesRegex(ValueError, "Unregistered PBP files: pbp_example_6.txt"):
            discover_pbp_examples(self.root, self.catalog)

    def test_new_fixture_cannot_be_silently_omitted(self):
        (self.root / "test_fixture_pbp_example_6.json").touch()
        with self.assertRaisesRegex(ValueError, "Unregistered PBP files: test_fixture_pbp_example_6.json"):
            discover_pbp_examples(self.root, self.catalog)

    def test_missing_fixture_or_snapshot_is_reported(self):
        for name in (self.example.fixture_file, self.example.snapshot_file):
            (self.root / name).unlink()
        with self.assertRaisesRegex(ValueError, "Missing PBP files:.*test_fixture_pbp_example_5.json.*test_fixture_pbp_example_5.txt"):
            discover_pbp_examples(self.root, self.catalog)

    def test_duplicate_example_numbers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate example numbers"):
            discover_pbp_examples(self.root, (self.example, self.example))


if __name__ == "__main__":
    unittest.main()
