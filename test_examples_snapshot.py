import unittest
from pathlib import Path
import subprocess
import re

from pbp_alignment import alignment_metrics


class TestExampleSnapshots(unittest.TestCase):

    def test_pbp_fixture_timestamps_are_valid_iso_datetimes(self):
        """Timestamp seeds retain their precision without duplicating time zones."""
        import json
        from datetime import datetime

        def check_timestamps(value, path):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in ('startTime', 'endTime', 'dateTime') and isinstance(item, str):
                        with self.subTest(field=f'{path}.{key}'):
                            datetime.fromisoformat(item.replace('Z', '+00:00'))
                    else:
                        check_timestamps(item, f'{path}.{key}')
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    check_timestamps(item, f'{path}[{index}]')

        for number in range(1, 5):
            path = Path(__file__).with_name(f'test_fixture_pbp_example_{number}.json')
            check_timestamps(json.loads(path.read_text()), path.name)

    def _get_example_logs(self):
        """Helper to read all example logs."""
        logs = {}
        examples_dir = Path(__file__).parent / "examples"
        for i in range(1, 11):
            example_file = examples_dir / f"game_{i:02d}.txt"
            with open(example_file, 'r') as f:
                logs[example_file.name] = f.read()
        return logs

    def test_examples_match_rendered_output(self):
        # Path to the directory containing example game logs
        examples_dir = Path(__file__).parent / "examples"

        # Iterate over each example game log
        for i in range(1, 11):
            example_file = examples_dir / f"game_{i:02d}.txt"
            with open(example_file, 'r') as f:
                snapshot = f.read()

            # Re-run the simulation with the same seed
            # The seed is the file number (e.g., 1 for game_01.txt)
            process = subprocess.run(
                ['python3', 'example_games.py', str(i)],
                capture_output=True,
                text=True,
                check=True
            )
            rendered_output = process.stdout

            # Compare the snapshot with the fresh output
            self.assertEqual(
                snapshot,
                rendered_output,
                f"Example log {example_file} is out of date; "
                "rerun python update_examples.py."
            )

    def test_no_contradictory_takes_and_hits_phrasing(self):
        example_logs = self._get_example_logs()
        batted_ball_results = ["Result: Groundout", "Result: Flyout", "Result: Single", "Result: Double", "Result: Triple", "Result: Home Run", "(", "lines out", "grounds out"]
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    if "takes the" in line:
                        self.assertFalse(any(res in line for res in batted_ball_results), f"Contradictory 'takes the' on a batted ball: {line}")

    def test_no_redundant_batter_name_in_play_by_play(self):
        example_logs = self._get_example_logs()
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    # Find lines that start with a batter's name
                    match = re.match(r"^\s*([A-Z][a-z]+(?: '[A-Z][a-z]+')? [A-Z][a-z]+) steps to the plate", line)
                    if not match:
                        continue

                    batter_name = match.group(1)
                    # Check the subsequent play-by-play lines for this at-bat
                    ab_lines = content.split(line)[1].split(" | ")[0]
                    for ab_line in ab_lines.splitlines():
                        if batter_name in ab_line:
                            # Check if the name appears more than once, ignoring the initial mention if it exists
                            self.assertEqual(ab_line.count(batter_name), 1, f"Redundant batter name found in line: '{ab_line}'")

    def test_no_clunky_strikeout_results(self):
        example_logs = self._get_example_logs()
        narrative_strikeout_phrases = ["down on strikes", "caught looking", "goes down swinging", "watches strike three go by", "frozen on a pitch"]
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    if any(phrase in line for phrase in narrative_strikeout_phrases):
                        self.assertNotIn("Result: Strikeout", line, f"Clunky strikeout result found: {line}")

    def test_no_double_foul_in_commentary(self):
        example_logs = self._get_example_logs()
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    foul_mentions = re.findall(r'foul', line, re.IGNORECASE)
                    self.assertLessEqual(len(foul_mentions), 1, f"Double 'foul' mention found: {line}")



    def _assert_pbp_alignment(self, target_file, fixture_file, jaccard_min, ngram_min, line_exact_min,
                              content_ngram_min, content_exact_min, content_jaccard_min=0.48,
                              target_skip=0, rendered_skip=0):
        """Guard coverage both with and without TTS playback timing markers."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        root = Path(__file__).resolve().parent
        with open(root / target_file) as f:
            text = '\n'.join(f.read().splitlines()[target_skip:])
        with open(root / fixture_file) as f:
            data = json.load(f)
        rendered = '\n'.join(NarrativeRenderer(data).render().splitlines()[rendered_skip:])

        metrics = alignment_metrics(text, rendered, content_only=False)
        content = alignment_metrics(text, rendered)
        checks = (
            ('Word Jaccard (all)', metrics.word_jaccard, jaccard_min),
            ('5-gram coverage (all)', metrics.ngram_coverage, ngram_min),
            ('Positional exact lines (all)', metrics.exact_fraction, line_exact_min),
            ('Word Jaccard (content)', content.word_jaccard, content_jaccard_min),
            ('5-gram coverage (content)', content.ngram_coverage, content_ngram_min),
            ('Positional exact lines (content)', content.exact_fraction, content_exact_min),
        )
        for label, actual, minimum in checks:
            with self.subTest(file=target_file, metric=label):
                self.assertGreaterEqual(
                    actual, minimum,
                    f'{label} ({actual*100:.2f}%) is below the {minimum*100:.2f}% threshold.'
                )

    def test_pbp_example_3_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_3.json meets a minimum threshold of match with pbp_example_3.txt."""
        self._assert_pbp_alignment(
            'pbp_example_3.txt', 'test_fixture_pbp_example_3.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            content_ngram_min=0.34, content_exact_min=0.09, content_jaccard_min=0.57,
            target_skip=33, rendered_skip=30,
        )


    def test_pbp_example_3_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_3.json matches test_fixture_pbp_example_3.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_3.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_3.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_3.json does not match test_fixture_pbp_example_3.txt. Note: If you see this failure after modifying test_fixture_pbp_example_3.json, it simply means you need to regenerate test_fixture_pbp_example_3.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_3.json --pbp-outfile test_fixture_pbp_example_3.txt`)."
        )

    def test_pbp_example_1_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_1.json meets a minimum threshold of match with pbp_example_1.txt."""
        self._assert_pbp_alignment(
            'pbp_example_1.txt', 'test_fixture_pbp_example_1.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            content_ngram_min=0.35, content_exact_min=0.24, content_jaccard_min=0.59,
            target_skip=28, rendered_skip=30,
        )

    def test_pbp_example_1_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_1.json matches test_fixture_pbp_example_1.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_1.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_1.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_1.json does not match test_fixture_pbp_example_1.txt. Note: If you see this failure after modifying test_fixture_pbp_example_1.json, it simply means you need to regenerate test_fixture_pbp_example_1.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_1.json --pbp-outfile test_fixture_pbp_example_1.txt`)."
        )

    def test_pbp_example_2_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_2.json meets a minimum threshold of match with pbp_example_2.txt."""
        self._assert_pbp_alignment(
            'pbp_example_2.txt', 'test_fixture_pbp_example_2.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            content_ngram_min=0.37, content_exact_min=0.25, content_jaccard_min=0.58,
            target_skip=35, rendered_skip=30,
        )

    def test_pbp_example_2_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_2.json matches test_fixture_pbp_example_2.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_2.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_2.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_2.json does not match test_fixture_pbp_example_2.txt. Note: If you see this failure after modifying test_fixture_pbp_example_2.json, it simply means you need to regenerate test_fixture_pbp_example_2.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_2.json --pbp-outfile test_fixture_pbp_example_2.txt`)."
        )

    def test_pbp_example_4_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_4.json meets a minimum threshold of match with pbp_example_4.txt."""
        self._assert_pbp_alignment(
            'pbp_example_4.txt', 'test_fixture_pbp_example_4.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            content_ngram_min=0.33, content_exact_min=0.20, content_jaccard_min=0.57,
            target_skip=27, rendered_skip=30,
        )

    def test_pbp_example_4_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_4.json matches test_fixture_pbp_example_4.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_4.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_4.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_4.json does not match test_fixture_pbp_example_4.txt. Note: If you see this failure after modifying test_fixture_pbp_example_4.json, it simply means you need to regenerate test_fixture_pbp_example_4.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_4.json --pbp-outfile test_fixture_pbp_example_4.txt`)."
        )

if __name__ == "__main__":
    unittest.main()
