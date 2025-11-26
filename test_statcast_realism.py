import unittest
import random
import copy
import io
from contextlib import redirect_stdout

from baseball import BaseballSimulator
from gameday_converter import GamedayConverter
from teams import TEAMS


class TestStatcastRealism(unittest.TestCase):
    def setUp(self):
        self.team1_data = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        self.team2_data = copy.deepcopy(TEAMS["PC_PILOTS"])
        random.seed(42)

    def test_strikeout_looking_consistency(self):
        """
        Ensures that a 'strikeout looking' is always preceded by a 'Called strike' event.
        """
        # We need to run a simulation and capture its output.
        simulator = BaseballSimulator(self.team1_data, self.team2_data)
        gameday_data = simulator.play_game()
        converter = GamedayConverter(gameday_data, commentary_style='statcast')
        output = converter.convert()

        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Check if this line contains a strikeout looking description
            if "strikes out looking" in line:
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

    def test_no_in_play_on_strikeout(self):
        """
        Ensures a strikeout is not labeled as 'In play'.
        """
        # Seed chosen to reliably produce a strikeout early in the game
        random.seed(1)
        simulator = BaseballSimulator(self.team1_data, self.team2_data)
        gameday_data = simulator.play_game()
        converter = GamedayConverter(gameday_data, commentary_style='statcast')
        output = converter.convert()

        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Check for a line indicating a strikeout result
            if "whiffs" in line or "goes down looking" in line or "strikes out swinging" in line:
                # The "In play" tag should not appear on the line just before the result.
                self.assertNotIn(
                    "In play", lines[i - 1],
                    f"Strikeout event '{line.strip()}' was incorrectly preceded by 'In play' line: '{lines[i - 1].strip()}'"
                )

    def test_no_infield_fly_to_outfield(self):
        """
        Ensures 'infield fly' is not used for flyouts to outfielders.
        """
        # Run a bunch of games to increase the chance of seeing the rare event.
        random.seed(123)
        output = ""
        for _ in range(20):  # More iterations
            simulator = BaseballSimulator(self.team1_data, self.team2_data)
            gameday_data = simulator.play_game()
            converter = GamedayConverter(gameday_data, commentary_style='statcast')
            output += converter.convert()

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
        output = ""
        for _ in range(50):
            simulator = BaseballSimulator(self.team1_data, self.team2_data)
            gameday_data = simulator.play_game()
            converter = GamedayConverter(gameday_data, commentary_style='statcast')
            output += converter.convert()

        lines = output.split('\n')
        for line in lines:
            if "Home Run" in line and "EV:" in line:
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


if __name__ == "__main__":
    unittest.main()
