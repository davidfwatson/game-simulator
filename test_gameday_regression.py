import json
import subprocess
import unittest
import copy
from baseball import BaseballSimulator
from teams import TEAMS

class TestGamedayRegression(unittest.TestCase):
    """
    Test that the full Gameday JSON output contains events with the expected structure.
    """
    gameday_data = None

    @classmethod
    def setUpClass(cls):
        """
        Run the simulation once to generate the full Gameday JSON output.
        This is more efficient than running the simulation for each test.
        """
        if cls.gameday_data is None:
            sim = BaseballSimulator(
                copy.deepcopy(TEAMS["BAY_BOMBERS"]),
                copy.deepcopy(TEAMS["PC_PILOTS"]),
                commentary_style='gameday'
            )
            sim.play_game()
            cls.gameday_data = sim.gameday_data

    def _find_event(self, event_type, details_code=None):
        """Helper to find the first occurrence of a specific event in the game data."""
        for play in self.gameday_data['liveData']['plays']['allPlays']:
            if play['result']['event'] == event_type:
                return play
            for event in play.get('playEvents', []):
                if event['details'].get('code') == details_code:
                    return event
        return None

    def _find_all_events(self, event_type):
        """Helper to find all occurrences of a specific event type."""
        return [p for p in self.gameday_data['liveData']['plays']['allPlays'] if p['result']['event'] == event_type]

    def test_game_data_structure(self):
        """Test the basic structure of the top-level gameData object."""
        self.assertIn('gameData', self.gameday_data)
        self.assertIn('teams', self.gameday_data['gameData'])
        self.assertIn('home', self.gameday_data['gameData']['teams'])
        self.assertIn('away', self.gameday_data['gameData']['teams'])
        self.assertIn('id', self.gameday_data['gameData']['teams']['home'])

    def test_live_data_structure(self):
        """Test the basic structure of the top-level liveData object."""
        self.assertIn('liveData', self.gameday_data)
        self.assertIn('plays', self.gameday_data['liveData'])
        self.assertIn('allPlays', self.gameday_data['liveData']['plays'])
        self.assertIn('linescore', self.gameday_data['liveData'])
        self.assertGreater(len(self.gameday_data['liveData']['plays']['allPlays']), 0)

    def test_pitch_event_ball(self):
        """Find a 'Ball' event and validate its structure."""
        event = self._find_event(None, details_code='B')
        self.assertIsNotNone(event, "Could not find a 'Ball' event in the game data.")
        self.assertIn('details', event)
        self.assertEqual(event['details']['code'], 'B')
        self.assertFalse(event['details']['isStrike'])
        self.assertIn('pitchData', event)
        self.assertIn('startSpeed', event['pitchData'])

    def test_pitch_event_called_strike(self):
        """Find a 'Called Strike' event and validate its structure."""
        event = self._find_event(None, details_code='C')
        self.assertIsNotNone(event, "Could not find a 'Called Strike' event in the game data.")
        self.assertEqual(event['details']['code'], 'C')
        self.assertTrue(event['details']['isStrike'])
        self.assertIn('pitchData', event)

    def test_play_event_home_run(self):
        """Find a 'Home Run' play and validate its structure."""
        hr_plays = self._find_all_events('Home Run')
        if not hr_plays:
            self.skipTest("No 'Home Run' events found in generated game data.")
        play = hr_plays[0]
        self.assertEqual(play['result']['event'], 'Home Run')
        self.assertGreater(play['result']['rbi'], 0)
        self.assertTrue(play['about']['isScoringPlay'])
        any_hr_has_hit_data = any('hitData' in e for p in hr_plays for e in p['playEvents'] if e['details'].get('code') == 'X')
        self.assertTrue(any_hr_has_hit_data, "No 'Home Run' play was found with hitData.")

    def test_play_event_groundout(self):
        """Find a 'Groundout' play and validate its structure."""
        play = self._find_event('Groundout')
        self.assertIsNotNone(play, "Could not find a 'Groundout' play in the game data.")
        self.assertEqual(play['result']['event'], 'Groundout')
        self.assertGreaterEqual(play['count']['outs'], 1)
        if play.get('runners'):
            self.assertGreater(len(play['runners'][0]['credits']), 0)
            self.assertIn(play['runners'][0]['credits'][0]['credit'], ['assist', 'putout'])

    def test_pitch_event_swinging_strike(self):
        """Find a 'Swinging Strike' event and validate its structure."""
        event = self._find_event(None, details_code='S')
        self.assertIsNotNone(event, "Could not find a 'Swinging Strike' event in the game data.")
        self.assertEqual(event['details']['code'], 'S')
        self.assertTrue(event['details']['isStrike'])

    def test_pitch_event_foul(self):
        """Find a 'Foul' event and validate its structure."""
        event = self._find_event(None, details_code='D')
        self.assertIsNotNone(event, "Could not find a 'Foul' event in the game data.")
        self.assertEqual(event['details']['code'], 'D')
        self.assertTrue(event['details']['isStrike'])

    def test_play_event_single(self):
        """Find a 'Single' play and validate its structure."""
        plays = self._find_all_events('Single')
        if not plays:
            self.skipTest("No 'Single' events found in generated game data.")
        self.assertEqual(plays[0]['result']['event'], 'Single')
        any_has_hit_data = any('hitData' in e for p in plays for e in p['playEvents'] if e['details'].get('code') == 'X')
        self.assertTrue(any_has_hit_data, "No 'Single' play was found with hitData.")

    def test_play_event_double(self):
        """Find a 'Double' play and validate its structure."""
        plays = self._find_all_events('Double')
        if not plays:
            self.skipTest("No 'Double' events found in generated game data.")
        self.assertEqual(plays[0]['result']['event'], 'Double')
        any_has_hit_data = any('hitData' in e for p in plays for e in p['playEvents'] if e['details'].get('code') == 'X')
        self.assertTrue(any_has_hit_data, "No 'Double' play was found with hitData.")

    def test_play_event_triple(self):
        """Find a 'Triple' play and validate its structure."""
        plays = self._find_all_events('Triple')
        if not plays:
            self.skipTest("No 'Triple' events found in the generated game data.")
        self.assertEqual(plays[0]['result']['event'], 'Triple')
        any_has_hit_data = any('hitData' in e for p in plays for e in p['playEvents'] if e['details'].get('code') == 'X')
        self.assertTrue(any_has_hit_data, "No 'Triple' play was found with hitData.")

    def test_play_event_flyout(self):
        """Find a 'Flyout' play and validate its structure."""
        play = self._find_event('Flyout')
        self.assertIsNotNone(play, "Could not find a 'Flyout' play in the game data.")
        self.assertEqual(play['result']['event'], 'Flyout')
        self.assertGreaterEqual(play['count']['outs'], 1)
        if play.get('runners'):
            self.assertGreater(len(play['runners'][0]['credits']), 0)
            self.assertEqual(play['runners'][0]['credits'][0]['credit'], 'putout')

if __name__ == "__main__":
    unittest.main()