import re
import unittest

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR
from pbp_comparison import (
    REPOSITORY_ROOT,
    compare_example,
    discover_pbp_examples,
    render_example,
)


class TestExampleSnapshots(unittest.TestCase):

    def _get_example_logs(self):
        """Read the current example catalog, independent of the working directory."""
        return {
            f"game_{index:02d}.txt": (EXAMPLES_DIR / f"game_{index:02d}.txt").read_text(encoding="utf-8")
            for index in range(1, len(EXAMPLE_GAMES) + 1)
        }

    def test_examples_match_rendered_output(self):
        for index, game in enumerate(EXAMPLE_GAMES, start=1):
            example_file = EXAMPLES_DIR / f"game_{index:02d}.txt"
            with self.subTest(file=example_file.name):
                self.assertEqual(
                    example_file.read_text(encoding="utf-8"),
                    game.render(),
                    f"Example log {example_file} is out of date; rerun python update_examples.py.",
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


class TestPBPExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Discovery deliberately fails if new references have no comparison
        # metadata or snapshots, rather than silently leaving them untested.
        cls.examples = discover_pbp_examples()
        cls.rendered = {example.number: render_example(example) for example in cls.examples}

    def test_pbp_match_percentages(self):
        for example in self.examples:
            with self.subTest(file=example.target_file):
                scores = compare_example(example, self.rendered[example.number])
                self.assertEqual(scores.failures(example), [], example.target_file)

    def test_pbp_draft_consistency(self):
        for example in self.examples:
            with self.subTest(file=example.fixture_file):
                expected = (REPOSITORY_ROOT / example.snapshot_file).read_text(encoding="utf-8")
                self.assertEqual(
                    self.rendered[example.number],
                    expected,
                    f"Snapshot for {example.fixture_file} is out of date; regenerate with "
                    f"python baseball.py --gameday-file {example.fixture_file} "
                    f"--pbp-outfile {example.snapshot_file}.",
                )


if __name__ == "__main__":
    unittest.main()
