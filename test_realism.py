import unittest
import random
import io
import re
import copy
from baseball import BaseballSimulator
from renderers import NarrativeRenderer, StatcastRenderer
from teams import TEAMS

class TestRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)
        self.home_team = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        self.away_team = copy.deepcopy(TEAMS["PC_PILOTS"])

        # Run the simulation and get the output from the simulator instance
        game = BaseballSimulator(self.home_team, self.away_team)
        game.play_game()
        renderer = NarrativeRenderer(game.gameday_data, seed=42)
        self.log = renderer.render()

    def test_quantized_velocities(self):
        """Test if pitch velocities are too uniform or 'quantized'."""
        # This test now runs on the statcast output, which reliably contains velocity data.
        game = BaseballSimulator(self.home_team, self.away_team)
        game.play_game()
        renderer = StatcastRenderer(game.gameday_data, seed=42)
        log = renderer.render()

        velocities = re.findall(r'(\d{2,3}\.\d) mph', log)
        self.assertGreater(len(velocities), 0, "No velocities found in game log.")
        unique_velocities = set(velocities)
        self.assertGreater(len(unique_velocities), 10, "Pitch velocities appear quantized and not varied enough.")

    def test_repetitive_phrasing(self):
        """Test for repetitive phrasing in play-by-play output."""
        # Find all lines describing a pitch outcome (ball, strike, foul).
        # New format: "And the pitch... Description. One and oh." or "The one-one pitch... Description."
        # Spoken counts end in "One and one." or "Two and two." etc.
        pitch_lines = re.findall(r'\.\.\. (.*?)\. (?:[A-Z][a-z]+(?: and [a-z]+)?)\.', self.log)

        self.assertGreater(len(pitch_lines), 0, "No pitch description lines found in the log.")

        # Check for variety. If all lines are identical, it's a failure.
        unique_phrases = set(pitch_lines)
        self.assertGreater(len(unique_phrases), 5, "Play-by-play phrasing is too repetitive.")

    def test_abstract_outcomes(self):
        """Test for abstract outcomes instead of specific scorer's notation."""
        # The new commentary is more abstract, so we look for descriptive verbs instead of just "Groundout."
        # This test now checks that fielder information is still present in the narrative.
        # Updated regex to match new phrasing variations (e.g. "Grounder to short", "Fly ball, to left", "into the glove of")
        out_lines = re.findall(r'(?:grounds out|flies out|pops out|Grounder|Roller|Dribbler|Fly ball|Line drive|Lined|Pop) .*to \w+', self.log)
        # Also check for fielder names/actions
        action_lines = re.findall(r'(?:scoops it up|makes the catch|into the glove)', self.log)

        self.assertGreater(len(out_lines) + len(action_lines), 0, "Outcomes lack specific fielder information.")

    def test_box_state_ui(self):
        """Test for the presence of the unrealistic '[1B]-[2B]-[3B]' base state UI."""
        self.assertNotIn("[1B]-[2B]-[3B]", self.log, "Unrealistic box-state UI is present.")

    def test_extra_innings_banner(self):
        """Test for unrealistic extra-innings banner text."""
        extra_inning_log = ""
        for i in range(10):
            game = BaseballSimulator(copy.deepcopy(TEAMS["BAY_BOMBERS"]), copy.deepcopy(TEAMS["PC_PILOTS"]), game_seed=i)
            game.play_game()
            renderer = NarrativeRenderer(game.gameday_data, seed=i)
            log = renderer.render()
            if "Extra Innings" in log or "inning 10" in log.lower(): # Adjusted check
                extra_inning_log = log
                break
        if extra_inning_log:
            self.assertNotIn("--- Extra Innings: Runner placed on second base ---", extra_inning_log, "Unrealistic extra-innings banner found.")

    def test_nicknames_in_substitutions(self):
        """Test for the use of nicknames in substitution announcements, which is unrealistic."""
        sub_lines = re.findall(r'--- Pitching Change for.*', self.log)
        pitchers_with_nicknames = [p for p in self.home_team['players'] + self.away_team['players'] if p['position']['abbreviation'] == 'P' and p.get('nickname')]
        self.assertTrue(len(pitchers_with_nicknames) > 0, "No pitchers with nicknames found for testing.")
        for line in sub_lines:
            for pitcher in pitchers_with_nicknames:
                self.assertNotIn(f"'{pitcher['nickname']}'", line, f"Nickname '{pitcher['nickname']}' found in substitution announcement: {line}")
                self.assertNotIn(f" {pitcher['nickname']} ", line, f"Nickname '{pitcher['nickname']}' found in substitution announcement: {line}")

    def test_game_context_missing(self):
        """Test if essential game context like venue, and weather is present (Umpires not listed in radio script)."""
        # self.assertIn("Umpires:", self.log, "Umpire information is missing from the pre-game summary.")
        # Weather is embedded in sentence - check for any of the intro phrases
        weather_regex = r"(perfect night for a ball game:|Conditions at first pitch:|We've got .* for tonight's contest|Weather tonight:|It's a beautiful night,|Current conditions:|A look at the weather:|For those keeping score at home, it's)"
        self.assertRegex(self.log, weather_regex, "Weather information is missing from the pre-game summary.")
        self.assertIn("Tonight, from", self.log, "Venue information is missing from the pre-game summary.")

    # test_bracketed_ui_flag removed as feature is deprecated in narrative mode

    def test_simulation_realism_over_multiple_games(self):
        """
        Run the simulation multiple times to check for realism issues identified by the analyst.
        """
        num_games = 100
        total_walks, total_hbps, total_dps, total_triples = 0, 0, 0, 0
        groundout_2_3_count, unassisted_3u_count = 0, 0
        flyouts, popouts = 0, 0
        for i in range(num_games):
            game = BaseballSimulator(
                copy.deepcopy(self.home_team),
                copy.deepcopy(self.away_team),
                game_seed=i
            )
            game.play_game()
            renderer = NarrativeRenderer(game.gameday_data, seed=i+1)
            log = renderer.render()

            total_walks += log.count("draws a walk")
            total_hbps += (log.count("Hit by Pitch") + log.count("hit by the pitch"))
            total_dps += log.lower().count("double play")
            total_triples += log.count("a triple")
            groundout_2_3_count += len(re.findall(r'grounds out to Catcher', log, re.IGNORECASE))
            unassisted_3u_count += len(re.findall(r'(?:grounds out|grounder|roller|chopper|dribbler|bounced?) to first', log, re.IGNORECASE))
            flyouts += len(re.findall(r'(?:flies out|lines out|hit in the air|fly ball|line drive) to (?:left|center|right)', log, re.IGNORECASE))
            popouts += len(re.findall(r'(?:pops out|popped up) (?:back to the mound|in front of the plate|to first|to second|to third|to short|on the infield)', log, re.IGNORECASE))
        self.assertGreater(total_walks, 50, "Very few walks over 100 games, indicates a problem with plate discipline logic.")
        self.assertGreater(total_hbps, 2, "Hit by pitches are missing from the simulation.")
        self.assertGreater(total_dps, 20, "Double plays are too rare or missing.")
        self.assertLess(total_triples, 30, "Too many triples, indicates an issue with hit outcome distribution.")
        self.assertLess(groundout_2_3_count, 5, "Unrealistically high number of 2-3 groundouts.")
        self.assertGreater(unassisted_3u_count, 10, "3U unassisted groundouts are not being logged correctly.")
        self.assertGreater(popouts, 0, "Infield fly balls are not being classified as 'Pop outs'.")
        self.assertGreater(flyouts, 10, "Outfield fly balls are not being classified as 'Flyouts'.")

    # def test_no_wp_or_pb_with_bases_empty(self):
    #    """
    #    Test that a wild pitch or passed ball does not occur when the bases are empty.
    #    Deprecated: Narrative output no longer contains explicit 'Bases:' state lines.
    #    """
    #    pass

if __name__ == '__main__':
    unittest.main()