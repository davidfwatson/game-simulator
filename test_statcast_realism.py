import unittest
import random
import copy
import io
from contextlib import redirect_stdout


from baseball import BaseballSimulator
from renderers import StatcastRenderer, NarrativeRenderer
from teams import TEAMS
from commentary import GAME_CONTEXT

class TestStatcastRealism(unittest.TestCase):
    def setUp(self):
        # deepcopy is essential to prevent state leakage between tests,
        # as the simulator modifies the team data it receives.
        self.team1_data = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        self.team2_data = copy.deepcopy(TEAMS["PC_PILOTS"])
        # Set a seed for reproducibility of tests
        random.seed(42)

        # Dummy data for renderer initialization
        self.dummy_gameday_data = {
            'gameData': {
                'teams': {
                    'home': self.team1_data,
                    'away': self.team2_data
                }
            },
            'liveData': { 'plays': {'allPlays': []}, 'linescore': {'teams': {'home': {'runs': 0}, 'away': {'runs': 0}}} }
        }

    def test_verb_accuracy_based_on_batted_ball_data(self):
        """
        Tests if the commentary verb accurately reflects the batted ball data (EV and LA).
        For example, a high EV, low LA hit should be described as a "liner," not a "bloop."
        """
        # Use renderer to test this logic
        renderer = StatcastRenderer(self.dummy_gameday_data, seed=42)

        # Test Case 1: High EV, low LA single -> "liner"
        # EV > 100, LA < 10
        phrase, _ = renderer._get_batted_ball_verb("Single", 105.0, 5.0)
        self.assertIn(phrase, GAME_CONTEXT['statcast_verbs']['Single']['verbs']['liner'] + GAME_CONTEXT['statcast_verbs']['Single']['nouns']['liner'])

        # Test Case 2: Low EV, medium LA single -> "bloop"
        # EV < 90, 10 < LA < 30
        phrase, _ = renderer._get_batted_ball_verb("Single", 85.0, 20.0)
        self.assertIn(phrase, GAME_CONTEXT['statcast_verbs']['Single']['verbs']['bloop'] + GAME_CONTEXT['statcast_verbs']['Single']['nouns']['bloop'])

        # Test Case 3: High EV, negative LA single -> "grounder"
        # EV > 95, LA < 0
        phrase, _ = renderer._get_batted_ball_verb("Single", 98.0, -5.0)
        self.assertIn(phrase, GAME_CONTEXT['statcast_verbs']['Single']['verbs']['grounder'] + GAME_CONTEXT['statcast_verbs']['Single']['nouns']['grounder'])

        # Test Case 4: High EV flyout -> "deep"
        # EV > 100, LA > 30
        phrase, _ = renderer._get_batted_ball_verb("Flyout", 102.0, 35.0)
        self.assertIn(phrase, GAME_CONTEXT['statcast_verbs']['Flyout']['verbs']['deep'] + GAME_CONTEXT['statcast_verbs']['Flyout']['nouns'].get('deep',[]))

        # Test Case 5: Low EV flyout -> "popup"
        # EV < 90, LA > 40
        phrase, _ = renderer._get_batted_ball_verb("Pop Out", 88.0, 45.0)
        self.assertIn(phrase, GAME_CONTEXT['statcast_verbs']['Pop Out']['verbs']['default'] + GAME_CONTEXT['statcast_verbs']['Pop Out']['nouns']['default'])

    def test_strikeout_looking_consistency(self):
        """
        Ensures that a 'strikeout looking' is always preceded by a 'Called strike' event.
        """
        looking_verbs = [v for v in GAME_CONTEXT['statcast_verbs']['Strikeout']['looking']]

        # We need to run a simulation and capture its output.
        game = BaseballSimulator(self.team1_data, self.team2_data, game_seed=42)
        game.play_game()

        renderer = StatcastRenderer(game.gameday_data, seed=42)
        output = renderer.render()

        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Check if this line contains a strikeout looking description
            if any(verb in line for verb in looking_verbs):
                # Search backwards for the last pitch event
                last_pitch_event = ""
                for j in range(i - 1, -1, -1):
                    if lines[j].strip().startswith("Called strike:") or lines[j].strip().startswith("Swinging strike:"):
                        last_pitch_event = lines[j]
                        break

                self.assertTrue(
                    last_pitch_event.strip().startswith("Called strike:"),
                    f"Strikeout looking was not preceded by a called strike.\nLine: {line}\nPrevious pitch: {last_pitch_event}"
                )

    def test_missing_statcast_data_handling(self):
        """
        Tests that the system can gracefully handle missing Statcast data fields.
        """
        # This test originally mocked internal print statements.
        # With the new architecture, we can verify that the renderer doesn't crash
        # when processing data with missing fields.

        # Manually construct a play with missing data
        self.dummy_gameday_data['liveData']['plays']['allPlays'] = [{
            'about': {'inning': 1, 'isTopInning': True},
            'matchup': {'batter': {'fullName': 'Test Batter'}, 'pitcher': {'id': 123, 'fullName': 'Test Pitcher'}},
            'count': {'outs': 0},
            'playEvents': [{
                'details': {'code': 'X', 'description': 'In play, no out', 'type': {'description': 'Fastball'}},
                'pitchData': {'startSpeed': 95.0},
                'hitData': {}, # Missing ev/la
                'count': {'balls': 0, 'strikes': 0}
            }],
            'result': {'event': 'Single', 'rbi': 0, 'homeScore': 0, 'awayScore': 0},
            'runners': []
        }]

        renderer = StatcastRenderer(self.dummy_gameday_data, seed=42)
        output = renderer.render()

        self.assertNotIn("EV:", output)
        self.assertNotIn("LA:", output)
        self.assertIn("Result:", output)


    def test_no_in_play_on_strikeout(self):
        """
        Ensures a strikeout is not labeled as 'In play'.
        """
        # Seed chosen to reliably produce a strikeout early in the game
        random.seed(1)
        game = BaseballSimulator(self.team1_data, self.team2_data, game_seed=1)
        game.play_game()

        renderer = StatcastRenderer(game.gameday_data, seed=1)
        output = renderer.render()

        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Check for a line indicating a strikeout result
            if "whiffs" in line or "goes down looking" in line or "strikes out swinging" in line:
                # The "In play" tag should not appear on the line just before the result.
                # Actually, in StatcastRenderer, "in play" line is generated from code 'X'.
                # A strikeout ends with code 'C' or 'S'.
                self.assertNotIn(
                    "In play", lines[i-1],
                    f"Strikeout event '{line.strip()}' was incorrectly preceded by 'In play' line: '{lines[i-1].strip()}'"
                )

    def test_no_infield_fly_to_outfield(self):
        """
        Ensures 'infield fly' is not used for flyouts to outfielders.
        """
        random.seed(123)
        for i in range(20): # More iterations
            game = BaseballSimulator(self.team1_data, self.team2_data, game_seed=i)
            game.play_game()

            renderer = StatcastRenderer(game.gameday_data, seed=i)
            output = renderer.render()

            outfield_positions = ['LF', 'CF', 'RF']
            lines = output.split('\n')
            for line in lines:
                if "infield fly" in line:
                    # Check if the fielder mentioned is an outfielder
                    is_outfielder_mentioned = any(f"to {pos}" in line for pos in outfield_positions)
                    self.assertFalse(
                        is_outfielder_mentioned,
                        f"Incorrectly labeled an 'infield fly' to an outfielder: {line.strip()}"
                    )

    def test_plausible_hr_batted_ball_data(self):
        """
        Ensures that generated Home Run data (EV, LA) is within plausible physical limits.
        """
        random.seed(456)
        for i in range(50):
            game = BaseballSimulator(self.team1_data, self.team2_data, game_seed=i)
            game.play_game()

            renderer = StatcastRenderer(game.gameday_data, seed=i)
            output = renderer.render()

            lines = output.split('\n')
            for line in lines:
                if "Home Run" in line and "EV:" in line:
                    # Example line: Result: Result: Home Run (EV: 118.2 mph, LA: 40.6°) ...
                    # Or just: Result: Home Run (EV: ...
                    try:
                        ev_str = line.split("EV: ")[1].split(" mph")[0]
                        la_str = line.split("LA: ")[1].split("°")[0]
                        ev = float(ev_str)
                        la = float(la_str)

                        if ev >= 118.0:
                            self.assertLess(
                                la, 35.0,
                                f"Implausible HR data: EV {ev} mph at LA {la}°"
                            )
                    except (IndexError, ValueError):
                        continue

    def test_plausible_popup_classification(self):
        """
        Ensures that 'popup' or 'infield fly' verbs are reserved for high-angle, typically low-EV flyouts.
        """
        renderer = StatcastRenderer(self.dummy_gameday_data)

        # A ball at 45 degrees with decent EV should be a fly ball, not a popup.
        phrase, _ = renderer._get_batted_ball_verb("Flyout", 95.0, 45.0)
        self.assertNotIn("popup", phrase)
        self.assertNotIn("infield fly", phrase)

        # A ball at 60 degrees, even with decent EV, is almost certainly a popup.
        phrase, _ = renderer._get_batted_ball_verb("Pop Out", 92.0, 60.0)
        popup_phrases = GAME_CONTEXT['statcast_verbs']['Pop Out']['verbs']['default'] + GAME_CONTEXT['statcast_verbs']['Pop Out']['nouns']['default']
        self.assertIn(phrase, popup_phrases)

        # A weakly hit ball at a high angle is a classic popup.
        phrase, _ = renderer._get_batted_ball_verb("Pop Out", 85.0, 55.0)
        self.assertIn(phrase, popup_phrases)


if __name__ == "__main__":
    unittest.main()