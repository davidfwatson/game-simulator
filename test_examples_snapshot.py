import unittest
from pathlib import Path

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR


class TestExampleSnapshots(unittest.TestCase):
    def test_examples_match_rendered_output(self):
        for index, game in enumerate(EXAMPLE_GAMES, start=1):
            expected_path = EXAMPLES_DIR / f"game_{index:02d}.txt"
            self.assertTrue(
                expected_path.exists(),
                msg=f"Missing example log for seed {game.seed}: {expected_path}",
            )
            expected_output = expected_path.read_text(encoding="utf-8")
            actual_output = game.render()
            self.assertEqual(
                actual_output,
                expected_output,
                msg=f"Example log {expected_path} is out of date; rerun python update_examples.py.",
            )


if __name__ == "__main__":
    unittest.main()
