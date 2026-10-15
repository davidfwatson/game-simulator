"""The engine tells players apart by name (bases, pitch budgets, batters
faced), so no two players on any rosters may share one."""
import collections
import unittest

from annotate_transcript_facts import _mentions
from teams import TEAMS


class TestRosterNames(unittest.TestCase):
    def test_no_name_is_shared_across_rosters(self):
        teams_by_name = collections.defaultdict(set)
        for key, team in TEAMS.items():
            for player in team['players'] + team.get('bench', []):
                teams_by_name[player['legal_name']].add(key)
        shared = {name: sorted(keys) for name, keys in teams_by_name.items() if len(keys) > 1}
        self.assertEqual(shared, {})

    def test_mentions_skips_an_empty_name(self):
        self.assertEqual(_mentions('Nobody here.', ['']), [])


if __name__ == '__main__':
    unittest.main()
