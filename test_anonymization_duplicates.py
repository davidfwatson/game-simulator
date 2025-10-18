"""
Test that anonymization doesn't create invalid scenarios like a player batting against themselves.
"""

import json
import unittest
from pathlib import Path


class TestAnonymizationDuplicates(unittest.TestCase):
    """Verify anonymized data doesn't have logical inconsistencies."""

    def setUp(self):
        """Load anonymized data."""
        self.anon_data_path = Path('anonymized_gameday_1.json')

        if not self.anon_data_path.exists():
            self.skipTest("anonymized_gameday_1.json not found")

        with open(self.anon_data_path) as f:
            self.anon_data = json.load(f)

    def test_batter_and_pitcher_have_different_ids(self):
        """Test that no play has the same player ID for batter and pitcher."""
        plays = self.anon_data.get('liveData', {}).get('plays', {}).get('allPlays', [])

        conflicts = []
        for i, play in enumerate(plays):
            matchup = play.get('matchup', {})
            batter = matchup.get('batter', {})
            pitcher = matchup.get('pitcher', {})

            batter_id = batter.get('id')
            pitcher_id = pitcher.get('id')

            if batter_id and pitcher_id and batter_id == pitcher_id:
                event = play.get('result', {}).get('event', 'Unknown')
                conflicts.append({
                    'play_index': i,
                    'player_id': batter_id,
                    'event': event
                })

        self.assertEqual(
            conflicts,
            [],
            f"Found {len(conflicts)} plays where batter and pitcher have same ID: {conflicts[:5]}"
        )

    def test_pitcher_not_on_bases(self):
        """Test that pitcher is never on the bases (invalid scenario)."""
        plays = self.anon_data.get('liveData', {}).get('plays', {}).get('allPlays', [])

        conflicts = []
        for i, play in enumerate(plays):
            matchup = play.get('matchup', {})
            pitcher_id = matchup.get('pitcher', {}).get('id')

            if not pitcher_id:
                continue

            # Check if pitcher is on any base
            for base in ['postOnFirst', 'postOnSecond', 'postOnThird']:
                if base in matchup and isinstance(matchup[base], dict):
                    base_runner_id = matchup[base].get('id')
                    if base_runner_id == pitcher_id:
                        conflicts.append({
                            'play_index': i,
                            'pitcher_id': pitcher_id,
                            'base': base,
                            'event': play.get('result', {}).get('event', 'Unknown')
                        })

        self.assertEqual(
            conflicts,
            [],
            f"Found {len(conflicts)} plays where pitcher is on base: {conflicts[:3]}"
        )


if __name__ == '__main__':
    unittest.main()
