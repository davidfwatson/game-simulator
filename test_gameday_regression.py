"""
This module contains the regression test for the MLB Gameday JSON output.

It works by reading a set of pre-generated JSON files from the
`examples/gameday/` directory and comparing them against the output of the
`BaseballSimulator` for a given seed.

If the simulation engine's behavior changes, the generated Gameday data will
no longer match the snapshots. To bless the new behavior, run the
`update_gameday_examples.py` script, which will overwrite the existing
snapshot files with the new output.
"""
import json
import unittest
from pathlib import Path

from example_games import EXAMPLE_GAMES, ExampleGame

GAMEDAY_EXAMPLES_DIR = Path(__file__).parent / "examples" / "gameday"


class TestGamedayRegression(unittest.TestCase):
    def test_gameday_snapshots(self):
        for index, game in enumerate(EXAMPLE_GAMES, start=1):
            with self.subTest(seed=game.seed):
                # Load the canonical snapshot from the examples/gameday/ directory
                snapshot_path = GAMEDAY_EXAMPLES_DIR / f"game_{index:02d}.json"
                with open(snapshot_path, "r") as f:
                    canonical_data = json.load(f)

                # Render the game with the same seed and capture the JSON output
                gameday_json_str = ExampleGame.render(game, commentary_style="gameday")
                generated_data = json.loads(gameday_json_str)

                # The generated JSON must exactly match the canonical snapshot
                self.assertEqual(generated_data, canonical_data)


if __name__ == "__main__":
    unittest.main()