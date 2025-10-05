import json
import unittest
from pathlib import Path

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR


class TestGamedayRegression(unittest.TestCase):
    def test_gameday_examples_match_rendered_output(self):
        for index, game in enumerate(EXAMPLE_GAMES, start=1):
            expected_path = EXAMPLES_DIR / f"gameday_game_{index:02d}.json"
            self.assertTrue(
                expected_path.exists(),
                msg=f"Missing Gameday example log for seed {game.seed}: {expected_path}",
            )

            # Load the expected output as a JSON object
            with expected_path.open('r', encoding='utf-8') as f:
                expected_json = json.load(f)

            # Render the game and load the actual output as a JSON object
            actual_output_str = game.render(commentary_style='gameday')
            try:
                actual_json = json.loads(actual_output_str)
            except json.JSONDecodeError:
                self.fail(f"Could not decode rendered Gameday JSON for seed {game.seed}.\nOutput:\n{actual_output_str}")

            # We can't do a direct comparison because timestamps and UUIDs will differ.
            # Instead, we'll compare the structure and key-values that should be deterministic.
            self.assertEqual(len(expected_json), len(actual_json),
                             msg=f"Gameday log for seed {game.seed} has a different number of events.")

            for i, (expected_event, actual_event) in enumerate(zip(expected_json, actual_json)):
                # Remove non-deterministic keys before comparison
                for key in ['playId', 'startTime', 'endTime', 'playEndTime']:
                    expected_event.pop(key, None)
                    actual_event.pop(key, None)

                self.assertEqual(
                    actual_event,
                    expected_event,
                    msg=(f"Gameday example log {expected_path.name} (event {i}) is out of date; "
                         f"rerun python update_gameday_examples.py.")
                )


if __name__ == "__main__":
    unittest.main()