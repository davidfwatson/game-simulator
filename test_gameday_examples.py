"""
Regression tests for gameday JSON output.

Tests that gameday JSON output remains consistent across code changes by
comparing against curated snapshots of representative plays from each game.
"""

import json
import unittest
from pathlib import Path

from example_games import EXAMPLE_GAMES
from gameday_snapshot_extractor import create_snapshot_data


class TestGamedayExamples(unittest.TestCase):
    """Test that gameday JSON output matches snapshots."""

    def test_gameday_snapshots_match_rendered_output(self):
        """
        Compare regenerated gameday snapshots against stored snapshots.

        This is similar to test_examples_snapshot.py but for gameday JSON.
        Instead of storing full games (too large), we store curated subsets
        of representative plays.
        """
        snapshots_dir = Path(__file__).parent / "examples" / "gameday_snapshots"

        # Iterate over each example game
        for i, example in enumerate(EXAMPLE_GAMES, start=1):
            snapshot_file = snapshots_dir / f"gameday_{i:02d}.json"

            with self.subTest(game=i):
                # Load stored snapshot
                with open(snapshot_file, 'r') as f:
                    stored_snapshot = json.load(f)

                # Regenerate gameday output with same seed
                regenerated_gameday_json = example.render(commentary_style="gameday")
                regenerated_gameday = json.loads(regenerated_gameday_json)

                # Extract snapshot from regenerated data
                regenerated_snapshot = create_snapshot_data(regenerated_gameday, max_plays=6)

                # Compare snapshots
                self.assertEqual(
                    stored_snapshot,
                    regenerated_snapshot,
                    f"Gameday snapshot for game {i:02d} has changed. "
                    f"If this is intentional, run: python update_gameday_examples.py"
                )

    def test_snapshot_play_diversity(self):
        """Verify that snapshots contain diverse event types."""
        snapshots_dir = Path(__file__).parent / "examples" / "gameday_snapshots"

        all_event_types = set()
        for i in range(1, 11):
            snapshot_file = snapshots_dir / f"gameday_{i:02d}.json"
            with open(snapshot_file, 'r') as f:
                snapshot = json.load(f)

            # Collect event types from this snapshot
            for play in snapshot['plays']:
                all_event_types.add(play['result']['event'])

        # Should have at least these basic event types across all games
        expected_types = {'Single', 'Groundout', 'Flyout', 'Strikeout'}
        missing_types = expected_types - all_event_types

        self.assertEqual(
            missing_types,
            set(),
            f"Snapshots are missing coverage of event types: {missing_types}"
        )

    def test_snapshot_structure(self):
        """Verify basic structure of each snapshot."""
        snapshots_dir = Path(__file__).parent / "examples" / "gameday_snapshots"

        for i in range(1, 11):
            snapshot_file = snapshots_dir / f"gameday_{i:02d}.json"

            with self.subTest(game=i):
                with open(snapshot_file, 'r') as f:
                    snapshot = json.load(f)

                # Check top-level structure
                self.assertIn('gameData', snapshot)
                self.assertIn('plays', snapshot)
                self.assertIn('metadata', snapshot)

                # Check plays structure
                self.assertIsInstance(snapshot['plays'], list)
                self.assertGreater(len(snapshot['plays']), 0)

                # Check each play has required fields
                for play in snapshot['plays']:
                    self.assertIn('result', play)
                    self.assertIn('about', play)
                    self.assertIn('count', play)
                    self.assertIn('playEvents', play)
                    self.assertIn('runners', play)


if __name__ == "__main__":
    unittest.main()
