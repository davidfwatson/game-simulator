"""
This module contains regression tests for the MLB Gameday JSON output.

Instead of storing full game JSONs (which are very large), this test uses
curated single-event examples to validate the structure and content of each
event type that the simulator can generate.

The example events are stored in examples/gameday_events/ directory.
"""
import json
import unittest
from pathlib import Path

GAMEDAY_EVENTS_DIR = Path(__file__).parent / "examples" / "gameday_events"


def load_event(event_name: str) -> dict:
    """Load a gameday event example from JSON file."""
    filepath = GAMEDAY_EVENTS_DIR / f"{event_name}.json"
    with open(filepath, 'r') as f:
        return json.load(f)


class TestGamedayRegression(unittest.TestCase):
    """Test that each gameday event type has the expected structure."""

    def test_pitch_ball(self):
        """Ball pitch event has correct structure."""
        event = load_event('pitch_ball')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['type']['code'], 'P')
        self.assertEqual(event['details']['code'], 'B')
        self.assertTrue(event['details']['isBall'])
        self.assertIn('pitchData', event)
        self.assertIn('startSpeed', event['pitchData'])
        self.assertIn('coordinates', event['pitchData'])
        self.assertIn('breaks', event['pitchData'])

    def test_pitch_called_strike(self):
        """Called strike event has correct structure."""
        event = load_event('pitch_called_strike')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'C')
        self.assertTrue(event['details']['isStrike'])
        self.assertIn('pitchData', event)

    def test_pitch_swinging_strike(self):
        """Swinging strike event has correct structure."""
        event = load_event('pitch_swinging_strike')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'S')
        self.assertTrue(event['details']['isStrike'])
        self.assertIn('pitchData', event)

    def test_pitch_foul(self):
        """Foul ball event has correct structure."""
        event = load_event('pitch_foul')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'D')
        self.assertTrue(event['details']['isStrike'])
        self.assertIn('pitchData', event)

    def test_pitch_in_play_single(self):
        """Single event has correct structure with hit data."""
        event = load_event('pitch_in_play_single')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'X')
        self.assertTrue(event['details']['isInPlay'])
        self.assertIn('Single', event['details']['description'])
        self.assertIn('hitData', event)
        self.assertIn('launchSpeed', event['hitData'])
        self.assertIn('launchAngle', event['hitData'])
        self.assertIn('trajectory', event['hitData'])

    def test_pitch_in_play_double(self):
        """Double event has correct structure with hit data."""
        event = load_event('pitch_in_play_double')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'X')
        self.assertTrue(event['details']['isInPlay'])
        self.assertIn('Double', event['details']['description'])
        self.assertIn('hitData', event)

    def test_pitch_in_play_triple(self):
        """Triple event has correct structure with hit data."""
        event = load_event('pitch_in_play_triple')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'X')
        self.assertTrue(event['details']['isInPlay'])
        self.assertIn('Triple', event['details']['description'])
        self.assertIn('hitData', event)

    def test_pitch_in_play_home_run(self):
        """Home run event has correct structure with hit data."""
        event = load_event('pitch_in_play_home_run')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'X')
        self.assertTrue(event['details']['isInPlay'])
        self.assertIn('Home Run', event['details']['description'])
        self.assertIn('hitData', event)

    def test_pitch_in_play_groundout(self):
        """Groundout event has correct structure with hit data."""
        event = load_event('pitch_in_play_groundout')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'X')
        self.assertTrue(event['details']['isInPlay'])
        self.assertIn('Groundout', event['details']['description'])
        self.assertIn('hitData', event)
        self.assertEqual(event['hitData']['trajectory'], 'ground_ball')

    def test_pitch_in_play_flyout(self):
        """Flyout event has correct structure with hit data."""
        event = load_event('pitch_in_play_flyout')
        self.assertTrue(event['isPitch'])
        self.assertEqual(event['details']['code'], 'X')
        self.assertTrue(event['details']['isInPlay'])
        self.assertIn('Flyout', event['details']['description'])
        self.assertIn('hitData', event)
        self.assertEqual(event['hitData']['trajectory'], 'fly_ball')

    def test_action_stolen_base(self):
        """Stolen base action has correct structure."""
        event = load_event('action_stolen_base')
        self.assertFalse(event['isPitch'])
        self.assertEqual(event['type']['code'], 'A')
        self.assertEqual(event['details']['code'], 'SB')
        self.assertEqual(event['details']['eventType'], 'stolen_base')
        self.assertIn('runners', event)
        self.assertFalse(event['runners'][0]['isOut'])

    def test_action_caught_stealing(self):
        """Caught stealing action has correct structure."""
        event = load_event('action_caught_stealing')
        self.assertFalse(event['isPitch'])
        self.assertEqual(event['type']['code'], 'A')
        self.assertEqual(event['details']['code'], 'CS')
        self.assertEqual(event['details']['eventType'], 'caught_stealing')
        self.assertIn('runners', event)
        self.assertTrue(event['runners'][0]['isOut'])
        self.assertIn('creditedFielders', event['runners'][0])


if __name__ == "__main__":
    unittest.main()
