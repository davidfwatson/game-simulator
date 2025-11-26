import unittest
import json
from gameday_converter import GamedayConverter


class TestGamedayConverter(unittest.TestCase):
    def test_converter_runs_without_errors(self):
        """
        Test that the GamedayConverter can process a real Gameday JSON file
        without raising any exceptions.
        """
        with open('real_gameday.json', 'r') as f:
            gameday_data = json.load(f)

        try:
            converter = GamedayConverter(gameday_data, commentary_style='narrative')
            output = converter.convert()
            self.assertIsInstance(output, str)
            self.assertGreater(len(output), 0)
        except Exception as e:
            self.fail(f"GamedayConverter raised an exception: {e}")


if __name__ == '__main__':
    unittest.main()
