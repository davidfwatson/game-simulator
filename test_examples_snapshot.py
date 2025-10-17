import unittest
from pathlib import Path
import subprocess
import re

class TestExampleSnapshots(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()