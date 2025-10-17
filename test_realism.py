import unittest
import random
import io
import re
import copy
from baseball import BaseballSimulator
from teams import TEAMS

class TestRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)
        self.home_team = copy.deepcopy(TEAMS["BAY_BOMBERS"])
        self.away_team = copy.deepcopy(TEAMS["PC_PILOTS"])

        # Run the simulation and get the output from the simulator instance
        game = BaseballSimulator(self.home_team, self.away_team, commentary_style='narrative')
        game.play_game()
        self.log = "\n".join(game.output_lines)

    def test_quantized_velocities(self):
        """Test if pitch velocities are too uniform or 'quantized'."""
        # This test now runs on the statcast output, which reliably contains velocity data.
        game = BaseballSimulator(self.home_team, self.away_team, commentary_style='statcast')
        game.play_game()
        log = "\n".join(game.output_lines)

        velocities = re.findall(r'(\d{2,3}\.\d) mph', log)
        self.assertGreater(len(velocities), 0, "No velocities found in game log.")
        unique_velocities = set(velocities)
        self.assertGreater(len(unique_velocities), 10, "Pitch velocities appear quantized and not varied enough.")

    def test_repetitive_phrasing(self):
        """Test for repetitive phrasing in play-by-play output."""
        # Find all lines describing a pitch outcome (ball, strike, foul).
        pitch_lines = re.findall(r'^\s\s(?!Result:)(?!\|)(?!Now batting:)(.+)\.', self.log, re.MULTILINE)
        self.assertGreater(len(pitch_lines), 0, "No pitch description lines found in the log.")

        # Check for variety. If all lines are identical, it's a failure.
        unique_phrases = set(pitch_lines)
        self.assertGreater(len(unique_phrases), 5, "Play-by-play phrasing is too repetitive.")

    def test_abstract_outcomes(self):
        """Test for abstract outcomes instead of specific scorer's notation."""
        # The new commentary is more abstract, so we look for descriptive verbs instead of just "Groundout."
        # This test now checks that fielder information is still present in the narrative.
        out_lines = re.findall(r'\w+ (?:grounds out|flies out|pops out) to \w+', self.log)
        self.assertGreater(len(out_lines), 0, "Outcomes lack specific fielder information.")

    def test_box_state_ui(self):
        """Test for the presence of the unrealistic '[1B]-[2B]-[3B]' base state UI."""
        self.assertNotIn("[1B]-[2B]-[3B]", self.log, "Unrealistic box-state UI is present.")

    def test_extra_innings_banner(self):
        """Test for unrealistic extra-innings banner text."""
        extra_inning_log = ""
        for i in range(10):
            random.seed(i)
            game = BaseballSimulator(copy.deepcopy(TEAMS["BAY_BOMBERS"]), copy.deepcopy(TEAMS["PC_PILOTS"]), commentary_style='narrative')
            game.play_game()
            log = "\n".join(game.output_lines)
            if "Extra Innings" in log:
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
        """Test if essential game context like umpires, venue, and weather is missing."""
        self.assertIn("Umpires:", self.log, "Umpire information is missing from the pre-game summary.")
        self.assertIn("Weather:", self.log, "Weather information is missing from the pre-game summary.")
        self.assertIn("Venue:", self.log, "Venue information is missing from the pre-game summary.")

    def test_bracketed_ui_flag(self):
        """Test that the bracketed UI flag correctly changes the base runner display."""
        game_bracketed = BaseballSimulator(copy.deepcopy(self.home_team), copy.deepcopy(self.away_team), use_bracketed_ui=True, commentary_style='narrative')
        game_bracketed.play_game()
        log_bracketed = "\n".join(game_bracketed.output_lines)
        self.assertIn("[", log_bracketed, "Bracketed UI not found when flag is enabled.")
        self.assertIn("]-", log_bracketed, "Bracketed UI not found when flag is enabled.")

        game_named = BaseballSimulator(copy.deepcopy(self.home_team), copy.deepcopy(self.away_team), use_bracketed_ui=False, commentary_style='narrative')
        game_named.play_game()
        log_named = "\n".join(game_named.output_lines)
        self.assertNotIn("[", log_named, "Bracketed UI found when flag is disabled.")
        self.assertNotIn("]-", log_named, "Bracketed UI found when flag is disabled.")

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
                commentary_style='narrative',
                game_seed=i,
                commentary_seed=i+1
            )
            game.play_game()
            log = "\n".join(game.output_lines)
            total_walks += log.count("draws a walk")
            total_hbps += log.count("Hit by Pitch")
            total_dps += log.lower().count("double play")
            total_triples += log.count("a triple")
            groundout_2_3_count += len(re.findall(r'grounds out to Catcher', log, re.IGNORECASE))
            unassisted_3u_count += len(re.findall(r'grounds out to first', log, re.IGNORECASE))
            flyouts += len(re.findall(r'(?:flies out|lines out) to (?:left|center|right)', log, re.IGNORECASE))
            popouts += len(re.findall(r'pops out (?:back to the mound|in front of the plate|to first|to second|to third|to short)', log, re.IGNORECASE))
        self.assertGreater(total_walks, 50, "Very few walks over 100 games, indicates a problem with plate discipline logic.")
        self.assertGreater(total_hbps, 2, "Hit by pitches are missing from the simulation.")
        self.assertGreater(total_dps, 20, "Double plays are too rare or missing.")
        self.assertLess(total_triples, 30, "Too many triples, indicates an issue with hit outcome distribution.")
        self.assertLess(groundout_2_3_count, 5, "Unrealistically high number of 2-3 groundouts.")
        self.assertGreater(unassisted_3u_count, 10, "3U unassisted groundouts are not being logged correctly.")
        self.assertGreater(popouts, 2, "Infield fly balls are not being classified as 'Pop outs'.")
        self.assertGreater(flyouts, 10, "Outfield fly balls are not being classified as 'Flyouts'.")

    def test_no_wp_or_pb_with_bases_empty(self):
        """
        Test that a wild pitch or passed ball does not occur when the bases are empty.
        """
        for i in range(50):
            random.seed(i)
            game = BaseballSimulator(copy.deepcopy(self.home_team), copy.deepcopy(self.away_team), commentary_style='narrative')
            game.play_game()
            log = "\n".join(game.output_lines)
            lines = log.split('\n')
            last_bases_state = ""
            for line in lines:
                if line.strip().startswith("Result:"):
                    if "Bases: " in line:
                        last_bases_state = line.split("Bases: ")[1].split(" | ")[0]
                if "Wild Pitch!" in line or "Passed Ball!" in line:
                    self.assertNotEqual(last_bases_state, "Bases empty",
                                        f"Impossible event: A wild pitch or passed ball occurred with the bases empty.\nLog Line: {line}")

if __name__ == '__main__':
    unittest.main()