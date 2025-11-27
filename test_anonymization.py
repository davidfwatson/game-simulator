"""
Test that anonymized gameday files contain no real MLB team or player data.
"""

import json
import unittest
from pathlib import Path
from teams import TEAMS


class TestAnonymization(unittest.TestCase):
    """Verify anonymized gameday data contains no real MLB references."""

    def setUp(self):
        """Load real and anonymized data."""
        self.real_data_path = Path('real_gameday.json')
        self.anon_data_path = Path('anonymized_gameday_1.json')

        if not self.real_data_path.exists():
            self.skipTest("real_gameday.json not found")
        if not self.anon_data_path.exists():
            self.skipTest("anonymized_gameday_1.json not found")

        with open(self.real_data_path) as f:
            self.real_data = json.load(f)

        with open(self.anon_data_path) as f:
            self.anon_data = json.load(f)

    def _extract_real_player_names(self):
        """Extract all real player names from real gameday data."""
        names = set()

        # From gameData.players
        if 'gameData' in self.real_data and 'players' in self.real_data['gameData']:
            for player_key, player in self.real_data['gameData']['players'].items():
                full_name = player.get('fullName', '')
                if full_name:
                    names.add(full_name)
                    # Also add first and last names separately for partial match detection
                    parts = full_name.split()
                    if len(parts) >= 2:
                        names.add(parts[0])  # First name
                        names.add(parts[-1])  # Last name

        return names

    def _extract_fictional_player_names(self):
        """Extract all fictional player names from TEAMS data and synthetic lists."""
        names = set()

        # From TEAMS
        for team in TEAMS.values():
            for player in team['players']:
                full_name = player['legal_name']
                names.add(full_name)
                parts = full_name.split()
                if len(parts) >= 2:
                    names.add(parts[0])
                    names.add(parts[-1])

        # From synthetic lists in anonymize_real_gameday.py
        # Duplicating here to avoid importing and potentially running the script or dealing with import issues
        synthetic_first_names = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie',
                       'Quinn', 'Drew', 'Avery', 'Reese', 'Dakota', 'Skyler', 'Parker']
        synthetic_last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson',
                      'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin']

        names.update(synthetic_first_names)
        names.update(synthetic_last_names)

        return names

    def _extract_real_team_names(self):
        """Extract real team names from real gameday data."""
        names = set()

        if 'gameData' in self.real_data and 'teams' in self.real_data['gameData']:
            for side in ['home', 'away']:
                if side in self.real_data['gameData']['teams']:
                    team = self.real_data['gameData']['teams'][side]
                    if 'name' in team:
                        names.add(team['name'])
                    if 'teamName' in team:
                        names.add(team['teamName'])
                    if 'locationName' in team:
                        names.add(team['locationName'])
                    if 'abbreviation' in team:
                        names.add(team['abbreviation'])

        return names

    def _extract_real_player_ids(self):
        """Extract all real player IDs from real gameday data."""
        ids = set()

        # From gameData.players
        if 'gameData' in self.real_data and 'players' in self.real_data['gameData']:
            for player_key, player in self.real_data['gameData']['players'].items():
                ids.add(player['id'])

        return ids

    def _extract_real_team_ids(self):
        """Extract real team IDs from real gameday data."""
        ids = set()

        if 'gameData' in self.real_data and 'teams' in self.real_data['gameData']:
            for side in ['home', 'away']:
                if side in self.real_data['gameData']['teams']:
                    ids.add(self.real_data['gameData']['teams'][side]['id'])

        return ids

    def test_no_real_player_names_in_json(self):
        """Test that no real player names appear anywhere in anonymized JSON."""
        import re

        real_names = self._extract_real_player_names()
        fictional_names = self._extract_fictional_player_names()

        # Convert anonymized data to string for searching
        anon_str = json.dumps(self.anon_data)

        # Common names that might appear coincidentally (too generic to check)
        common_names = {'Chris', 'Kevin', 'Matt', 'Mike', 'John', 'David', 'Ryan', 'Alex', 'Ben'}

        # Baseball terms that aren't player names (but might be last names like "Pop" in "Zach Pop")
        baseball_terms = {'Pop'}  # From "Pop Out" event

        found_names = []
        for name in real_names:
            # Skip names that are also in our fictional universe
            if name in fictional_names:
                continue

            # Skip overly common first names
            if name in common_names:
                continue

            # Skip baseball terminology
            if name in baseball_terms:
                continue

            # Use word boundary matching to avoid substring matches
            # (e.g., "Bo" in "Bombers" or "about")
            pattern = r'\b' + re.escape(name) + r'\b'
            if re.search(pattern, anon_str):
                found_names.append(name)

        self.assertEqual(
            found_names,
            [],
            f"Found real player names in anonymized data: {found_names}"
        )

    def test_no_real_team_names_in_json(self):
        """Test that no real team names appear in anonymized JSON."""
        real_teams = self._extract_real_team_names()

        # Convert anonymized data to string for searching
        anon_str = json.dumps(self.anon_data)

        found_teams = []
        for team in real_teams:
            if team in anon_str:
                found_teams.append(team)

        self.assertEqual(
            found_teams,
            [],
            f"Found real team names in anonymized data: {found_teams}"
        )

    def test_no_real_player_ids_in_json(self):
        """Test that no real player IDs appear in anonymized JSON."""
        real_ids = self._extract_real_player_ids()

        def find_ids_in_data(data, path=""):
            """Recursively find all numeric IDs in data structure."""
            found = []

            if isinstance(data, dict):
                for key, value in data.items():
                    if key in ['id'] and isinstance(value, int):
                        if value in real_ids:
                            found.append((path + f".{key}", value))
                    found.extend(find_ids_in_data(value, path + f".{key}"))
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    found.extend(find_ids_in_data(item, path + f"[{i}]"))

            return found

        found_ids = find_ids_in_data(self.anon_data)

        self.assertEqual(
            found_ids,
            [],
            f"Found real player IDs in anonymized data: {found_ids[:10]}"  # Show first 10
        )

    def test_no_real_team_ids_in_json(self):
        """Test that no real team IDs appear in anonymized JSON."""
        real_team_ids = self._extract_real_team_ids()

        def find_team_ids_in_data(data, path=""):
            """Recursively find team IDs in data structure."""
            found = []

            if isinstance(data, dict):
                # Check if this dict has team-related keys
                if 'teams' in path or 'team' in path.lower():
                    if 'id' in data and isinstance(data['id'], int):
                        if data['id'] in real_team_ids:
                            found.append((path + ".id", data['id']))

                for key, value in data.items():
                    found.extend(find_team_ids_in_data(value, path + f".{key}"))
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    found.extend(find_team_ids_in_data(item, path + f"[{i}]"))

            return found

        found_ids = find_team_ids_in_data(self.anon_data)

        self.assertEqual(
            found_ids,
            [],
            f"Found real team IDs in anonymized data: {found_ids}"
        )

    def test_anonymized_data_has_fictional_teams(self):
        """Verify anonymized data uses our fictional teams."""
        expected_teams = {'Bay Area Bombers', 'Pacific City Pilots', 'BAY', 'PCP', 'Bombers', 'Pilots'}

        anon_str = json.dumps(self.anon_data)

        found = []
        for team in expected_teams:
            if team in anon_str:
                found.append(team)

        # Should find at least some of our fictional teams
        self.assertGreater(
            len(found),
            0,
            "Anonymized data should contain our fictional team names"
        )

    def test_play_count_preserved(self):
        """Verify anonymization preserves the number of plays."""
        real_plays = len(self.real_data.get('liveData', {}).get('plays', {}).get('allPlays', []))
        anon_plays = len(self.anon_data.get('liveData', {}).get('plays', {}).get('allPlays', []))

        self.assertEqual(
            real_plays,
            anon_plays,
            f"Play count mismatch: real={real_plays}, anonymized={anon_plays}"
        )


if __name__ == '__main__':
    unittest.main()
