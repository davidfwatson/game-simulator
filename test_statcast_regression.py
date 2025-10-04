import unittest
from pathlib import Path

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR


class TestStatcastRegression(unittest.TestCase):
    def test_statcast_examples_match_rendered_output(self):
        for index, game in enumerate(EXAMPLE_GAMES, start=1):
            # This will need to be updated to point to statcast examples
            expected_path = EXAMPLES_DIR / f"statcast_game_{index:02d}.txt"
            self.assertTrue(
                expected_path.exists(),
                msg=f"Missing statcast example log for seed {game.seed}: {expected_path}",
            )
            expected_output = expected_path.read_text(encoding="utf-8")
            actual_output = game.render(commentary_style='statcast')
            self.assertEqual(
                actual_output,
                expected_output,
                msg=f"Statcast example log {expected_path} is out of date; rerun python update_statcast_examples.py.",
            )


if __name__ == "__main__":
    unittest.main()