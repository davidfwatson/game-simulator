import unittest
from pathlib import Path
import subprocess

class TestStatcastRegression(unittest.TestCase):
    def test_statcast_examples_match_rendered_output(self):
        # Path to the directory containing example game logs
        examples_dir = Path(__file__).parent / "examples"

        # Iterate over each example game log
        for i in range(1, 11):
            example_file = examples_dir / f"statcast_game_{i:02d}.txt"
            with open(example_file, 'r') as f:
                snapshot = f.read()

            # Re-run the simulation with the same seed and statcast commentary
            process = subprocess.run(
                ['python3', 'example_games.py', str(i), '--commentary', 'statcast'],
                capture_output=True,
                text=True,
                check=True
            )
            rendered_output = process.stdout

            # Compare the snapshot with the fresh output
            self.assertEqual(
                snapshot,
                rendered_output,
                f"Statcast example log {example_file} is out of date; "
                "rerun python update_statcast_examples.py."
            )

if __name__ == "__main__":
    unittest.main()