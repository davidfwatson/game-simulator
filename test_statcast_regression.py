import unittest
from pathlib import Path

from example_games import EXAMPLE_GAMES


class TestStatcastRegression(unittest.TestCase):
    def test_statcast_examples_match_rendered_output(self):
        # Path to the directory containing example game logs
        examples_dir = Path(__file__).parent / "examples"

        # Iterate over each example game log
        for i, example in enumerate(EXAMPLE_GAMES, start=1):
            example_file = examples_dir / f"statcast_game_{i:02d}.txt"
            with open(example_file, 'r') as f:
                snapshot = f.read()

            # Re-run the simulation with the same seed and statcast commentary
            rendered_output = example.render(commentary_style="statcast")

            # Compare the snapshot with the fresh output
            self.assertEqual(
                snapshot,
                rendered_output,
                f"Statcast example log {example_file} is out of date; "
                "rerun python update_statcast_examples.py."
            )

if __name__ == "__main__":
    unittest.main()
