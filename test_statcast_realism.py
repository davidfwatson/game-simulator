import unittest
import random
import copy
import io
from contextlib import redirect_stdout


from baseball import BaseballSimulator
from teams import TEAMS
from commentary import GAME_CONTEXT
from renderers import StatcastRenderer

class TestStatcastRealism(unittest.TestCase):
    def setUp(self):
        # deepcopy is essential to prevent state leakage between tests,
        # as the simulator modifies the team data it receives.
        self.team1_data = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        self.team2_data = copy.deepcopy(TEAMS["PC_PILOTS"])
        # Set a seed for reproducibility of tests
        random.seed(42)

    def test_verb_accuracy_based_on_batted_ball_data(self):
        """
        Tests if the commentary verb accurately reflects the batted ball data (EV and LA).
        For example, a high EV, low LA hit should be described as a "liner," not a "bloop."
        """
        # We need an instance of StatcastRenderer.
        # We can pass dummy gameday data since we are testing the verb helper directly.
        renderer = StatcastRenderer({}, commentary_seed=42)

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

        simulator = BaseballSimulator(self.team1_data, self.team2_data, commentary_style='statcast')
        simulator.play_game()
        renderer = StatcastRenderer(simulator.gameday_data)
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
        # We can verify this by checking that a standard simulation doesn't crash
        # and produces plausible output, as data omission is now probabilistic.
        simulator = BaseballSimulator(self.team1_data, self.team2_data, commentary_style='statcast')
        simulator.play_game()
        renderer = StatcastRenderer(simulator.gameday_data)
        output = renderer.render()
        self.assertIn("Result:", output)

    def test_no_in_play_on_strikeout(self):
        """
        Ensures a strikeout is not labeled as 'In play'.
        """
        # Seed chosen to reliably produce a strikeout early in the game
        random.seed(1)
        simulator = BaseballSimulator(self.team1_data, self.team2_data, commentary_style='statcast')
        simulator.play_game()
        renderer = StatcastRenderer(simulator.gameday_data)
        output = renderer.render()

        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Check for a line indicating a strikeout result
            if "whiffs" in line or "goes down looking" in line or "strikes out swinging" in line:
                # The "In play" tag should not appear on the line just before the result.
                self.assertNotIn(
                    "In play", lines[i-1],
                    f"Strikeout event '{line.strip()}' was incorrectly preceded by 'In play' line: '{lines[i-1].strip()}'"
                )

    def test_no_infield_fly_to_outfield(self):
        """
        Ensures 'infield fly' is not used for flyouts to outfielders.
        """
        # Run a bunch of games to increase the chance of seeing the rare event.
        random.seed(123)
        for _ in range(20): # More iterations
            simulator = BaseballSimulator(self.team1_data, self.team2_data, commentary_style='statcast')
            simulator.play_game()
            renderer = StatcastRenderer(simulator.gameday_data)
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
        Specifically, it checks for and fails on extremely high EV with extremely high LA.
        """
        # A high number of iterations is needed to catch these rare events
        random.seed(456)
        for _ in range(50):
            simulator = BaseballSimulator(self.team1_data, self.team2_data, commentary_style='statcast')
            simulator.play_game()
            renderer = StatcastRenderer(simulator.gameday_data)
            output = renderer.render()

            lines = output.split('\n')
            for line in lines:
                if "Home Run" in line and "EV:" in line:
                    # Example line: In play, run(s). (EV: 118.2 mph, LA: 40.6°)
                    try:
                        ev_str = line.split("EV: ")[1].split(" mph")[0]
                        la_str = line.split("LA: ")[1].split("°")[0]
                        ev = float(ev_str)
                        la = float(la_str)

                        # A 118+ mph batted ball is almost physically impossible to hit at a 35+ degree angle.
                        # This is a key "tell" of a simulation.
                        if ev >= 118.0:
                            self.assertLess(
                                la, 35.0,
                                f"Implausible HR data: EV {ev} mph at LA {la}°"
                            )
                    except (IndexError, ValueError):
                        # Ignore lines where parsing fails; we only care about valid data lines.
                        continue

    def test_plausible_popup_classification(self):
        """
        Ensures that 'popup' or 'infield fly' verbs are reserved for high-angle, typically low-EV flyouts.
        """
        renderer = StatcastRenderer({}, commentary_seed=42)

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